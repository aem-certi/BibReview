"""
Módulo de utilitários para formatação e limpeza de strings, incluindo
funções de formatação de referências no estilo Vancouver.
"""

import re
import unidecode


def clean_text(text: str, to_lower: bool = True) -> str:
    """
    Limpa e normaliza texto, removendo caracteres especiais excessivos,
    acentos e espaços no início/fim.

    Args:
        text (str): Texto de entrada a ser limpo.
        to_lower (bool, optional): Se True, converte para letras minúsculas.
            Defaults to True.

    Returns:
        str: Texto limpo e normalizado.
    """
    if not text:
        return ""

    # Remove espaços no início/fim
    text = text.strip()

    # Remove acentos
    text = unidecode.unidecode(text)

    # (Opcional) converte para minúsculas
    if to_lower:
        text = text.lower()

    # Remove caracteres especiais em excesso, mantendo letras, dígitos, pontuação básica, e espaços
    text = re.sub(r"[^a-zA-Z0-9\s\.,;:\-\(\)\[\]]", "", text)

    # Remove múltiplos espaços
    text = re.sub(r"\s+", " ", text).strip()

    return text


def format_vancouver_authors(authors: list[str], max_authors: int = 6) -> str:
    """
    Recebe uma lista de autores (strings) e retorna uma string formatada no estilo Vancouver.
    Se houver mais de 'max_authors' autores, adiciona 'et al.' após o sexto autor.

    Exemplo:
        Entrada: ["Silva JA", "Souza MR", "Santos P", "Costa R", ...]
        Retorno: "Silva JA, Souza MR, Santos P, Costa R, et al."

    Args:
        authors (list[str]): Lista de nomes dos autores. 
            Espera nomes já normalizados (ex.: "Silva JA").
        max_authors (int, optional): Número máximo de autores antes de inserir 'et al.'.
            Defaults to 6.

    Returns:
        str: String de autores formatada no estilo Vancouver.
    """
    if not authors:
        return ""

    # Se a lista de autores for maior que max_authors, cortamos e adicionamos et al.
    if len(authors) > max_authors:
        truncated = authors[:max_authors]
        truncated.append("et al.")
        return ", ".join(truncated)
    else:
        return ", ".join(authors)


def format_vancouver_reference(
    authors: list[str],
    title: str,
    journal: str,
    year: str,
    volume: str = "",
    issue: str = "",
    pages: str = ""
) -> str:
    """
    Gera uma referência bibliográfica no estilo Vancouver de forma simples.
    Exemplo de saída: 
        "Silva JA, Souza MR, Santos P. Machine Learning em MOFs. 
         Journal of Advanced Materials. 2022;15(3):213-220."

    Args:
        authors (list[str]): Lista de autores (já no formato "Silva JA", por exemplo).
        title (str): Título do artigo.
        journal (str): Nome do periódico.
        year (str): Ano de publicação.
        volume (str, optional): Volume. Defaults to "".
        issue (str, optional): Número/fascículo (issue). Defaults to "".
        pages (str, optional): Páginas (ex.: "213-220"). Defaults to "".

    Returns:
        str: Referência formatada em estilo Vancouver simplificado.
    """
    # Formata autores
    authors_str = format_vancouver_authors(authors)

    # Monta referência
    ref = f"{authors_str}. {title}. {journal}. {year}"
    if volume:
        ref += f";{volume}"
        if issue:
            ref += f"({issue})"
        if pages:
            ref += f":{pages}."
        else:
            ref += "."
    else:
        # Se não tem volume, mas tem páginas, iremos colocar?
        if pages:
            ref += f";{pages}."
        else:
            ref += "."

    return ref
