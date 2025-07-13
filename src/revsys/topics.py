"""
Módulo para sugestão de tópicos, escrita de seções e polimento final da revisão.
"""
import os
import json
import openai
from revsys.config import GPT_MODEL, GENERATION_TEMPERATURE

__all__ = ['suggest_topics', 'write_topic', 'polish_review']

def suggest_topics(question: str, docs: list[dict], top_n: int = 5) -> list[str]:
    """
    Sugere tópicos para a revisão com base na pergunta e nos resumos dos artigos.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY não encontrado para sugestão de tópicos')
    # Instancia cliente OpenAI
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    system = "You are a systematic review expert who suggests topics for literature reviews."
    snippets = '\n'.join(f"- {doc.get('Summary','')}" for doc in docs[: min(len(docs),20)])
    user = (
        f"Research question: {question}\n"
        f"Document summaries:\n{snippets}\n"
        f"Please suggest up to {top_n} high-level review topics as a JSON array of strings."
    )
    resp = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{'role':'system','content':system},{'role':'user','content':user}],
        temperature=GENERATION_TEMPERATURE
    )
    content = resp.choices[0].message.content
    try:
        topics = json.loads(content)
    except json.JSONDecodeError:
        # Extrai array JSON
        start = content.find('[')
        end = content.rfind(']')
        topics = json.loads(content[start:end+1])
    return topics

def write_topic(topic: str, question: str, docs: list[dict], inclusion_criteria: list[str], exclusion_criteria: list[str]) -> str:
    """
    Escreve o texto para um tópico específico, usando os resumos dos artigos.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY não encontrado para escrita de tópico')
    # Instancia cliente OpenAI
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    system = "You are a scientific writing assistant specialized in literature reviews."
    # Prepara contexto
    docs_text = '\n'.join(f"- {doc.get('Summary','')}" for doc in docs[: min(len(docs),20)])
    user = (
        f"Research question: {question}\n"
        f"Inclusion criteria: {inclusion_criteria}\n"
        f"Exclusion criteria: {exclusion_criteria}\n"
        f"Topic: {topic}\n"
        "Write a structured section for this topic, including contextualization, comparison of studies, datasets used (public or private), and references."
        f"Use the following document summaries as reference:\n{docs_text}"
    )
    resp = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{'role':'system','content':system},{'role':'user','content':user}],
        temperature=GENERATION_TEMPERATURE
    )
    return resp.choices[0].message.content.strip()

def polish_review(question: str, inclusion_criteria: list[str], exclusion_criteria: list[str], topics_content: dict) -> str:
    """
    Consolida e polimentos todos os textos de tópicos em um documento final.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY não encontrado para polimento')
    # Instancia cliente OpenAI
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    system = "You are an expert editor polishing systematic literature reviews."
    # Monta texto inicial
    sections = '\n\n'.join(f"## {title}\n{text}" for title, text in topics_content.items())
    user = (
        f"Research question: {question}\n"
        f"Inclusion criteria: {inclusion_criteria}\n"
        f"Exclusion criteria: {exclusion_criteria}\n"
        "Polish and improve the following review sections to ensure coherence, technical accuracy, and fluent scientific style:\n"
        f"{sections}"
    )
    resp = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{'role':'system','content':system},{'role':'user','content':user}],
        temperature=GENERATION_TEMPERATURE
    )
    return resp.choices[0].message.content.strip()