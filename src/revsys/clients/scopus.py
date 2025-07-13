
"""
Módulo para busca de referências de artigos científicos na API do Scopus.

A classe ScopusFetcher permite a recuperação de metadados de artigos mediante consultas
à API do Scopus. Os dados obtidos são organizados em um DataFrame do Pandas, garantindo
um formato padronizado com as demais APIs.

Principais funcionalidades da classe:
- Busca de artigos com base em consultas personalizadas.
- Paginação automática para obtenção de múltiplos resultados.
- Padronização dos registros para garantir a consistência dos dados.
- Retorno dos dados em formato de DataFrame do Pandas.
"""

import requests
import pandas as pd
from typing import Optional, Dict, Any
from revsys.http_retry import retry_on_fail
import pdb

# Define as colunas padrão para todos os registros
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

class ScopusFetcher:
    """Classe para buscar referências de artigos na API do Scopus.
    
    Organiza os metadados dos artigos obtidos da API do Scopus em um DataFrame padronizado,
    retornando-o diretamente sem salvar em arquivo.
    """
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
    
    @retry_on_fail
    def _fetch_scopus_page(self, query: str, count: int, start: int, date_research: str) -> Dict[str, Any]:
        url = "https://api.elsevier.com/content/search/scopus"
        params = {
            "query": query,
            # "count": count, #essa var que estava dando erro no scopus. É o máximo de returns por busca.
            "start": start,
            "date": date_research
        }
        headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self.api_key,
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Erro: {response.status_code}, {response.text}")
        return response.json()
    
    def fetch_references(self, query: str, count: int = 25, date_research: str = "2022-2025") -> pd.DataFrame:
        all_articles = []
        start = 0
        
        while True:
            try:
                data = self._fetch_scopus_page(query, count, start, date_research)
            except Exception as e:
                print(f"Erro ao buscar a página iniciada em {start}: {e}")
                break
            
            entries = data.get("search-results", {}).get("entry", [])
            if not entries:
                print("Nenhum resultado retornado. Encerrando iteração.")
                break
            for result in entries:

                title = result.get("dc:title", "N/A")
                authors = result.get("dc:creator", "N/A")
                cover_date = result.get("prism:coverDate", "N/A")
                publication_year = cover_date.split("-")[0] if cover_date != "N/A" else "N/A"
                doi = result.get("prism:doi", "N/A")
                journal = result.get("prism:publicationName", "N/A")
                eid = result.get("eid", "N/A")
                abstract = result.get("dc:description", "N/A")
                cited_by_count = result.get("citedby-count", "N/A")
                
                # Criação do campo "Authors Year": último nome do primeiro autor + ano
                first_author = authors.split(",")[0].strip() if authors != "N/A" else "unknown"
                authors_year = f"{first_author} {publication_year}"
                
                language = "N/A"
                is_accepted = "N/A"
                is_published = "Yes" if journal != "N/A" else "No"
                type_ = "Scopus"
                type_crossref = "N/A"
                indexed_in = "Scopus"
                is_oa = "N/A"
                oa_status = "N/A"
                download_url = "N/A"
                
                registro = {
                    "ID": eid,
                    "Authors": authors,
                    "Authors Year": authors_year,
                    "Title": title,
                    "Journal": journal,
                    "Publication Year": publication_year,
                    "Publication Date": cover_date,
                    "Abstract": abstract,
                    "DOI": doi,
                    "Language": language,
                    "Is Accepted": is_accepted,
                    "Is Published": is_published,
                    "Type": type_,
                    "Type Crossref": type_crossref,
                    "Indexed In": indexed_in,
                    "Is Open Access": is_oa,
                    "OA Status": oa_status,
                    "Download URL": download_url,
                    "Cited By Count": cited_by_count,
                    "API": "scopus"
                }
                registro = padroniza_registro(registro)
                all_articles.append(registro)
            
            print(f"Processados {len(entries)} resultados a partir do offset {start}.")
            if len(entries) <= count:
                break
            
            start += count
        df = pd.DataFrame(all_articles)
        df = df.reindex(columns=STANDARD_COLUMNS)
        return df
