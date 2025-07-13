"""
Módulo para definição automática de diretrizes de revisão (pergunta, critérios e query).
"""
import os
import json
import openai
from revsys.config import GPT_MODEL, GENERATION_TEMPERATURE

__all__ = ['define_directives']

def define_directives(topic: str) -> dict:
    """
    Gera diretrizes de revisão sistemática a partir de um tema.

    Args:
        topic: descrição breve do tema de revisão (em inglês é preferível).

    Returns:
        Dicionário com chaves:
            research_question (str),
            inclusion_criteria (list[str]),
            exclusion_criteria (list[str]),
            inclusion_keys (list[str]),
            exclusion_keys (list[str]),
            search_query (str)
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY não encontrado para definição de diretrizes')
    # Instancia cliente OpenAI
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    system = (
        "You are an assistant that defines systematic review directives."
    )
    user = (
        f"Research topic: {topic}\n"
        "Please output a JSON object with EXACTLY the following keys: "
        "research_question (string), inclusion_criteria (list of strings), "
        "exclusion_criteria (list of strings), inclusion_keys (list of strings), "
        "exclusion_keys (list of strings), search_query (boolean query string)."
    )
    import warnings
    # Chama o LLM para gerar diretrizes
    try:
        resp = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user}
            ],
            temperature=GENERATION_TEMPERATURE
        )
    except Exception as e:
        # Fallback em caso de falha na chamada à API
        warnings.warn(f"define_directives API call failed: {e}")
        return {
            'research_question': topic,
            'inclusion_criteria': [],
            'exclusion_criteria': [],
            'inclusion_keys': [],
            'exclusion_keys': [],
            'search_query': topic
        }
    content = resp.choices[0].message.content
    # Extrai JSON do conteúdo de forma robusta
    directives = None
    try:
        decoder = json.JSONDecoder()
        directives, _ = decoder.raw_decode(content)
    except json.JSONDecodeError:
        # Tenta buscar trecho JSON delimitado por chaves
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            try:
                directives = json.loads(content[start:end+1])
            except json.JSONDecodeError:
                directives = None
    except Exception:
        directives = None
    # Se parsing falhar, retorna fallback
    if not isinstance(directives, dict):
        warnings.warn("define_directives parsing failed; using fallback directives")
        return {
            'research_question': topic,
            'inclusion_criteria': [],
            'exclusion_criteria': [],
            'inclusion_keys': [],
            'exclusion_keys': [],
            'search_query': topic
        }
    # Garante que todas as chaves existam
    result = {
        'research_question': directives.get('research_question', topic),
        'inclusion_criteria': directives.get('inclusion_criteria', []),
        'exclusion_criteria': directives.get('exclusion_criteria', []),
        'inclusion_keys': directives.get('inclusion_keys', []),
        'exclusion_keys': directives.get('exclusion_keys', []),
        'search_query': directives.get('search_query', topic)
    }
    return result