"""
Módulo para busca de referências de artigos científicos na API do PLOS.

A classe PlosAPI permite a recuperação de metadados de artigos através da API do PLOS. 
Os dados obtidos são organizados em um DataFrame do Pandas, com as mesmas colunas que das demais saídades
das APIs. 

Principais funcionalidades da classe:
- Busca de artigos com base em consultas / query. 
- Extração e formatação dos dados em um formato estruturado.
- Suporte à paginação automática para obtenção de múltiplos resultados.
- Retorno dos dados em formato de DataFrame do Pandas, com colunas padronizadas.
"""

import requests
import pandas as pd
from typing import List, Dict, Any, Optional
from revsys.http_retry import retry_on_fail

STANDARD_COLUMNS = [
    "ID", "Authors", "Authors Year", "Title", "Journal", "Publication Year",
    "Publication Date", "Abstract", "DOI", "Language", "Is Accepted", "Is Published",
    "Type", "Type Crossref", "Indexed In", "Is Open Access", "OA Status",
    "Download URL", "Cited By Count", "API"
]

def padroniza_registro(registro: dict) -> dict:
    for coluna in STANDARD_COLUMNS:
        if coluna not in registro:
            registro[coluna] = "N/A"
    return registro

class PlosAPI:
    """Classe para buscar referências de artigos na API do PLOS e retornar um DataFrame padronizado."""

    def __init__(self, base_url: str = "http://api.plos.org/search", rows: int = 25) -> None:
        self.base_url = base_url
        self.rows = rows

    @retry_on_fail
    def fetch_data(self, query: str, start: int = 0) -> dict:
        params = {
            "q": query,
            "rows": self.rows,
            "start": start,
            "fl": "id,title_display,journal,publication_date,article_type,author_display,abstract",
            "wt": "json"
        }
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        return response.json()

    def process_data(self, data: dict) -> list:
        records = []
        docs = data.get("response", {}).get("docs", [])
        for doc in docs:
            # ID e DOI (utilizamos o mesmo campo)
            article_id = doc.get("id", "N/A")
            title = doc.get("title_display", "N/A")
            journal = doc.get("journal", "N/A")
            pub_date_full = doc.get("publication_date", "N/A")
            if pub_date_full != "N/A" and "T" in pub_date_full:
                pub_date = pub_date_full.split("T")[0]
                pub_year = pub_date.split("-")[0]
            else:
                pub_date = pub_date_full
                pub_year = "N/A"
            article_type = doc.get("article_type", "N/A")
            # Autores
            authors_list = doc.get("author_display", [])
            authors = ", ".join(authors_list) if authors_list else "N/A"
            # Gera Authors Year baseado na quantidade de autores
            if authors_list:
                first_author = authors_list[0]
                if len(authors_list) == 1:
                    authors_year = f"{first_author.split()[-1]} {pub_year}"
                elif len(authors_list) == 2:
                    second_author = authors_list[1]
                    authors_year = f"{first_author.split()[-1]} and {second_author.split()[-1]} {pub_year}"
                else:
                    authors_year = f"{first_author.split()[-1]} et al. {pub_year}"
            else:
                authors_year = f"N/A {pub_year}"
            # Abstract (pode ser lista ou string)
            abstract_field = doc.get("abstract", [])
            if isinstance(abstract_field, list):
                abstract = " ".join(abstract_field).strip()
            else:
                abstract = abstract_field or "N/A"

            registro = {
                "ID": article_id,
                "Authors": authors,
                "Authors Year": authors_year,
                "Title": title,
                "Journal": journal,
                "Publication Year": pub_year,
                "Publication Date": pub_date,
                "Abstract": abstract,
                "DOI": article_id,
                "Language": "N/A",          # PLOS não fornece idioma
                "Is Accepted": "N/A",        # Não fornecido
                "Is Published": "Yes",       # Se retornado, já foi publicado
                "Type": article_type,
                "Type Crossref": article_type,
                "Indexed In": "PLOS",
                "Is Open Access": "Yes",     # PLOS é Open Access
                "OA Status": "PLOS Open Access",
                "Download URL": "N/A",       # Não fornecido pela API
                "Cited By Count": "N/A",     # Não fornecido
                "API": "plos"
            }
            registro = padroniza_registro(registro)
            records.append(registro)
        return records

    def run_pipeline(self, query: str, max_records: int = None) -> pd.DataFrame:
        all_records = []
        start = 0
        while True:
            data = self.fetch_data(query, start=start)
            records = self.process_data(data)
            if not records:
                break
            all_records.extend(records)
            if max_records and len(all_records) >= max_records:
                all_records = all_records[:max_records]
                break
            start += self.rows
            total_found = data.get("response", {}).get("numFound", 0)
            if start >= total_found:
                break
        df = pd.DataFrame(all_records)

        df = df.reindex(columns=STANDARD_COLUMNS)
        return df



# if __name__ == "__main__":
#     plos_api = PlosAPI(rows=25)
#     df_resultado = plos_api.run_pipeline(query=query, max_records=10)
#     print(df_resultado.head())
