"""
Script para coleta e padronização de metadados de artigos científicos disponíveis no arXiv.

Este módulo define a classe `ArxivFetcher`, responsável por:
1. Consultar a API do arXiv (em formato XML via protocolo Atom);
2. Extrair e estruturar os metadados relevantes de cada artigo, como autores, título, data, DOI, resumo, etc;
3. Aplicar filtros por ano de publicação, se especificados;
4. Padronizar os registros conforme um modelo comum definido na lista `STANDARD_COLUMNS`;
5. Retornar os dados organizados em um `pandas.DataFrame`.
"""


import requests
import pandas as pd
import xml.etree.ElementTree as ET
from revsys.http_retry import retry_on_fail

# Define as colunas padrão para extrair informações 
# dos metadados. 
STANDARD_COLUMNS = [
    "ID", "Authors", "Authors Year", "Title", "Journal", "Publication Year",
    "Publication Date", "Abstract", "DOI", "Language", "Is Accepted", "Is Published",
    "Type", "Type Crossref", "Indexed In", "Is Open Access", "OA Status",
    "Download URL", "Cited By Count", "API"
]

def padroniza_registro(registro: dict) -> dict:
    # Garante que todas as colunas padrão estejam presentes no registro
    for coluna in STANDARD_COLUMNS:
        if coluna not in registro:
            registro[coluna] = "N/A"
    return registro

class ArxivFetcher:
    """Classe para buscar referências de papers no arXiv e retornar um DataFrame padronizado."""
    def __init__(self) -> None:
        # Define namespaces para parsing do XML retornado pela API do arXiv
        self.ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/"
        }

    @retry_on_fail
    def _fetch_arxiv_page(self, query: str, start: int, max_results: int) -> ET.Element:
        base_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results
        }
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            raise Exception(f"Erro: {response.status_code}, {response.text}")
        root = ET.fromstring(response.content)
        return root

    def fetch_references(
        self,
        query: str,
        max_results: int = 100,
        start_year: int = None,
        end_year: int = None,
        total_limit: int = None
    ) -> pd.DataFrame:
        all_articles = []
        start = 0
        collected = 0

        while True:
            root = self._fetch_arxiv_page(query, start, max_results)
            entries = root.findall("atom:entry", self.ns)
            if not entries:
                print("Nenhum resultado retornado. Encerrando iteração.")
                break

            for entry in entries:
                # Data de publicação, ex.: "2025-01-06T09:19:23Z"
                published = entry.find("atom:published", self.ns).text.strip()
                published_date_only = published.split("T")[0] if "T" in published else published
                pub_year = int(published_date_only.split("-")[0])

                # Aplica filtros de data, se definidos
                if start_year and pub_year < start_year:
                    continue
                if end_year and pub_year > end_year:
                    continue

                # ID do arXiv (URL do registro)
                id_url = entry.find("atom:id", self.ns).text.strip()

                # Título
                title_elem = entry.find("atom:title", self.ns)
                title_str = title_elem.text.strip().replace("\n", " ") if title_elem is not None else "N/A"

                # Autores
                authors_list = [
                    author.find("atom:name", self.ns).text.strip()
                    for author in entry.findall("atom:author", self.ns)
                    if author.find("atom:name", self.ns) is not None
                ]
                authors_str = ", ".join(authors_list) if authors_list else "N/A"

                # Formata "Authors Year" conforme número de autores
                if authors_list:
                    if len(authors_list) == 1:
                        authors_year = f"{authors_list[0].split()[-1]} {pub_year}"
                    elif len(authors_list) == 2:
                        authors_year = f"{authors_list[0].split()[-1]} and {authors_list[1].split()[-1]} {pub_year}"
                    else:
                        authors_year = f"{authors_list[0].split()[-1]} et al. {pub_year}"
                else:
                    authors_year = f"unknown {pub_year}"

                # DOI e Journal
                doi_elem = entry.find("arxiv:doi", self.ns)
                doi = doi_elem.text.strip() if doi_elem is not None else "N/A"
                journal_elem = entry.find("arxiv:journal_ref", self.ns)
                journal = journal_elem.text.strip() if journal_elem is not None else "N/A"

                # Abstract
                abstract_elem = entry.find("atom:summary", self.ns)
                abstract = abstract_elem.text.strip().replace("\n", " ") if abstract_elem is not None else "N/A"

                # Download URL (busca link com title="pdf")
                download_url = "N/A"
                for link in entry.findall("atom:link", self.ns):
                    if link.attrib.get("title") == "pdf":
                        download_url = link.attrib.get("href")
                        break

                registro = {
                    "ID": doi if doi != "N/A" else id_url,
                    "Authors": authors_str,
                    "Authors Year": authors_year,
                    "Title": title_str,
                    "Journal": journal,
                    "Publication Year": pub_year,
                    "Publication Date": published_date_only,
                    "Abstract": abstract,
                    "DOI": doi,
                    "Language": "N/A",          # arXiv não informa idioma
                    "Is Accepted": "N/A",         # Não fornecido pela API
                    "Is Published": "Yes" if journal != "N/A" else "No",
                    "Type": "arXiv",
                    "Type Crossref": "N/A",
                    "Indexed In": "arXiv",
                    "Is Open Access": "Yes",      # arXiv é Open Access
                    "OA Status": "Open Access",
                    "Download URL": download_url,
                    "Cited By Count": "N/A"       # arXiv não fornece contagem de citações
                    ,"API": "arxiv"
                }

                registro = padroniza_registro(registro)
                all_articles.append(registro)
                collected += 1

                if total_limit and collected >= total_limit:
                    break

            print(f"Processados {len(entries)} resultados a partir do offset {start} (coletados {collected}).")

            if len(entries) < max_results or (total_limit and collected >= total_limit):
                break

            start += max_results

        df = pd.DataFrame(all_articles)
        df = df.reindex(columns=STANDARD_COLUMNS)
        return df


# if __name__ == "__main__":
#     fetcher = ArxivFetcher()
#     q = '''("Interstitial Lung Disease" OR "Pulmonary Fibrosis") AND "Segmentation"'''
#     df_arxiv = fetcher.fetch_references(
#         query=q, 
#         max_results=10,      # número de resultados por página
#         start_year=2023,     # filtra artigos com ano >= 2023
#         end_year=2025,       # filtra artigos com ano <= 2025
#         total_limit=20       # limita a coleta a 20 artigos
#     )
#     print(df_arxiv.head())
