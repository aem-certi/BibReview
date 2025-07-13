"""
Módulo para RAG: chunking de texto, criação de vetor store e recuperação de trechos.
"""
import os
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from revsys.config import EMBEDDING_MODEL

__all__ = ['chunk_text', 'build_vector_store', 'retrieve']

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """
    Divide texto bruto em chunks de tamanho aproximado (caracteres), com sobreposição.
    """
    if not text:
        return []
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap if end < length else end
    return chunks

def build_vector_store(chunks: list[str]) -> dict:
    """
    Gera embeddings para cada chunk e retorna um dicionário contendo:
        'chunks': lista de textos,
        'embeddings': numpy.ndarray de forma (n_chunks, dim)
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY não encontrado para RAG')
    # Instancia cliente OpenAI
    client = OpenAI(api_key=api_key)
    # Gera embeddings em lote
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=chunks)
    emb = np.array([d.embedding for d in resp.data])
    return {'chunks': chunks, 'embeddings': emb}

def retrieve(query: str, store: dict, top_k: int = 5) -> list[str]:
    """
    Recupera os top_k chunks mais similares à query, usando cosine similarity.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY não encontrado para RAG')
    # Instancia cliente OpenAI
    client = OpenAI(api_key=api_key)
    # Embedding da query
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    q_emb = np.array(resp.data[0].embedding).reshape(1, -1)
    # Cálculo de similaridade
    emb = store.get('embeddings')
    sims = cosine_similarity(q_emb, emb)[0]
    # Obtém índices ordenados
    idxs = np.argsort(sims)[::-1][:top_k]
    return [store['chunks'][i] for i in idxs]