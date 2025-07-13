"""
Módulo de pré-triagem de artigos usando embeddings e similaridade semântica.
"""
import os
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from revsys.config import EMBEDDING_MODEL
import pdb

__all__ = ['pretriage_records']

def pretriage_records(
    records: list[dict],
    inclusion_keys: list[str],
    exclusion_keys: list[str] = None,
    incl_threshold: float = 0.3,
    excl_threshold: float = 0.3
) -> list[dict]:
    """
    Realiza pré-triagem de registros com base em similaridade de embeddings.

    Args:
        records: lista de dicionários com chaves 'Title' e 'Abstract'.
        inclusion_keys: termos-chave para inclusão.
        exclusion_keys: termos-chave para exclusão (opcional).
        incl_threshold: similaridade mínima para inclusão.
        excl_threshold: similaridade máxima para exclusão.

    Returns:
        Lista filtrada de registros, adicionando 'score_inclusion' e 'score_exclusion'.
    """
    # Se não houver termos de inclusão, não há pré-triagem
    if not inclusion_keys:
        return records
    # Configura chave da OpenAI (obrigatória para pré-triagem semântica)
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY não encontrado para pré-triagem')
    # Instancia cliente OpenAI
    client = OpenAI(api_key=api_key)
    # Helper para criar embeddings que suporta nova e antiga interface

    def _create_embeddings_separate(model, inputs_list, data1):
        # If there are no more embeddings to process, just return the data
        if not inputs_list:
            return np.concatenate((data1,))
        
        resp = client.embeddings.create(model=model, input=inputs_list)
        try:
            data2 = np.array([d.embedding for d in resp['data']])
        except Exception as e:
            # If there's an error processing the next batch of embeddings, just return the previous data
            print(f"Error processing next 500 embeddings: {e}")
            return np.concatenate((data1,))
        
        return _create_embeddings_separate(model, inputs_list[500:], np.concatenate((data1, data2)))

    def _create_embeddings(model, inputs_list):
        # Tenta usar novo cliente (OpenAI.embeddings)
        try:
            resp = client.embeddings.create(model=model, input=inputs_list[:500])  # Process only the first 500 embeddings
            try:
                return resp.data
            except Exception as e:
                print(f"Error processing first 500 embeddings: {e}")
                # Return the first 500 embeddings and process the rest separately
                data1 = np.array([d.embedding for d in resp['data']])
                inputs_list_2 = inputs_list[500:]
                return _create_embeddings_separate(model, inputs_list_2, data1)
        except Exception as e:
            # Fallback para método antigo
            print(f"Error to create embeddings: {e}")
            import openai
            resp = openai.Embedding.create(model=model, input=inputs_list[:500])
            return np.array([d.embedding for d in resp['data']])

    # def _create_embeddings(model, inputs_list):
    #     # Tenta usar novo cliente (OpenAI.embeddings)
    #     try:
    #         resp = client.embeddings.create(model=model, input=inputs_list)
    #         try:
    #             return resp.data
    #         except Exception:
    #             return resp['data']
    #     except Exception:
    #         # Fallback para método antigo
    #         print('Error to create embeddings')
    #         # import openai
    #         # resp = openai.Embedding.create(model=model, input=inputs_list)
    #         # return resp['data']
    # # Se não houver registros, nada a processar
    # if not records:
    #     return records

    # Construir textos para embed
    
    texts = []
    for rec in records:
        title = rec.get('Title', '') or ''
        abstract = rec.get('Abstract', '') or ''
        texts.append(f"{title} {abstract}")
    # Embed registros e termos-chave
    # Inclusão
    incl_inputs = inclusion_keys
    # Embeddings de termos de inclusão
    incl_data = _create_embeddings(EMBEDDING_MODEL, incl_inputs)
    incl_emb = np.array([d.embedding for d in incl_data])
    # Exclusão
    excl_emb = None
    if exclusion_keys:
        excl_data = _create_embeddings(EMBEDDING_MODEL, exclusion_keys)
        excl_emb = np.array([d.embedding for d in excl_data])

    # Embeddings de registros (pode ser em lote)
    # Embeddings dos registros
    txt_data = _create_embeddings(EMBEDDING_MODEL, texts)
    txt_emb = np.array([d.embedding for d in txt_data])

    # Cálculo de similaridades
    sim_incl = cosine_similarity(txt_emb, incl_emb).max(axis=1)
    sim_excl = None

    if excl_emb is not None:
        sim_excl = cosine_similarity(txt_emb, excl_emb).max(axis=1)
    else:
        sim_excl = np.zeros_like(sim_incl)

    # Filtra registros
    filtered = []
    for rec, score_i, score_e in zip(records, sim_incl, sim_excl):
        # Marcar scores no registro
        rec['score_inclusion'] = float(score_i)
        rec['score_exclusion'] = float(score_e)
        if score_i >= incl_threshold and score_e <= excl_threshold:
            filtered.append(rec)
    return filtered