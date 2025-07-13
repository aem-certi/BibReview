"""
Script para consultar e padronizar metadados de artigos científicos usando a API do Crossref.

Esta implementação define a classe `CrossrefAPI`, que permite:
1. Consultar a API REST do Crossref com uma query textual;
2. Extrair metadados relevantes (título, autores, ano, DOI, etc);
3. Padronizar os registros em um formato comum, com colunas definidas em `STANDARD_COLUMNS`;
4. Retornar os resultados como um DataFrame do pandas.
"""

import re
import requests
import pdb
# from revsys.http_retry import retry_on_fail
import pandas as pd
from typing import List, Dict, Any, Optional
# IMPORTANT: Na requisição trás apenas papers - ignora livros, resumos em congressos etc

# Colunas padronizadas que o DataFrame final deve conter
STANDARD_COLUMNS = [
    "ID", "Authors", "Authors Year", "Title", "Journal", "Publication Year",
    "Publication Date", "Abstract", "DOI", "Language", "Is Accepted", "Is Published",
    "Type", "Type Crossref", "Indexed In", "Is Open Access", "OA Status",
    "Download URL", "Cited By Count", "API"
]

def padroniza_registro(registro: dict) -> dict:
    """Garante que todas as colunas esperadas estejam presentes no dicionário."""
    for coluna in STANDARD_COLUMNS:
        if coluna not in registro:
            registro[coluna] = "N/A"
    return registro

class CrossrefAPI:
    """
    Classe para buscar referências de publicações na API REST do Crossref
    e retornar um DataFrame padronizado.
    """

    def __init__(self, base_url: str = "https://api.crossref.org/works", rows: int = 25) -> None:
        self.base_url = base_url
        self.rows = rows

    # @retry_on_fail
    def fetch_data(self,
                   query: str,
                   offset: int = 0,
                   from_date: str = None,
                   to_date: str = None) -> dict:
        """
        Consulta a API Crossref com filtros opcionais de data.
        """
        # Construir filtros
        filters = ["type:journal-article"]
        if from_date:
            filters.append(f"from-pub-date:{from_date}")
        if to_date:
            filters.append(f"until-pub-date:{to_date}")
        params = {
            "query": query,
            "rows": self.rows,
            "offset": offset,
            "filter": ",".join(filters)
        }
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        return response.json()


    def _format_authors_year(self, authors_data: list, pub_year: str) -> str:
        """Formata os nomes dos autores + ano de publicação (ex: Silva et al. 2023)."""
        if not authors_data:
            return f"Unknown {pub_year}"
        names = []
        for author in authors_data:
            given = author.get("given", "")
            family = author.get("family", "")
            full_name = f"{given} {family}".strip()
            if full_name:
                names.append(full_name)
        if len(names)==0:
            return f"{pub_year}"
        if len(names) == 1:
            last_name = names[0].split()[-1]
            return f"{last_name} {pub_year}"
        elif len(names) == 2:
            last_name1 = names[0].split()[-1]
            last_name2 = names[1].split()[-1]
            return f"{last_name1} and {last_name2} {pub_year}"
        else:
            last_name = names[0].split()[-1]
            return f"{last_name} et al. {pub_year}"

    def process_data(self, data: dict) -> list:
        """Processa os dados JSON retornados pela API e extrai os campos relevantes."""
        records = []
        items = data.get("message", {}).get("items", [])
        for item in items:
            # removed try wrapper to restore original flow
            doi = item.get("DOI", "N/A")
            title_list = item.get("title", [])
            title = title_list[0] if title_list else "N/A"
            container_list = item.get("container-title", [])
            journal = container_list[0] if container_list else "N/A"
            issued = item.get("issued", {}).get("date-parts", [])
            if issued and len(issued) > 0 and len(issued[0]) > 0:
                pub_year = str(issued[0][0])
                pub_date = "-".join(str(part) for part in issued[0])
            else:
                pub_year = "N/A"
                pub_date = "N/A"
            authors_data = item.get("author", [])
            authors_list = []
            if authors_data:
                for author in authors_data:
                    given = author.get("given", "")
                    family = author.get("family", "")
                    full_name = f"{given} {family}".strip()
                    if full_name:
                        authors_list.append(full_name)
            authors = ", ".join(authors_list) if authors_list else "N/A"
            authors_year = self._format_authors_year(authors_data, pub_year)
            # Extract and clean abstract (remove HTML tags)
            raw_abstract = item.get("abstract", "")
            # Limpeza robusta de HTML e entidades
            if isinstance(raw_abstract, str) and raw_abstract.strip() and raw_abstract.strip().upper() != 'N/A':
                # Remove tags HTML
                cleaned = re.sub(r'<[^>]+>', '', raw_abstract)
                try:
                    from html import unescape as _unescape
                    abstract = _unescape(cleaned)
                except ImportError:
                    abstract = cleaned
                # Colapsa espaços em branco
                abstract = re.sub(r'\s+', ' ', abstract).strip()
            else:
                abstract = "N/A"
            language = item.get("language", "N/A")
            is_accepted = "N/A"
            is_published = "Yes" if pub_date != "N/A" else "No"
            type_val = item.get("type", "N/A")
            type_crossref = type_val
            indexed_in = "Crossref"
            license_info = item.get("license", [])
            if license_info and isinstance(license_info, list) and len(license_info) > 0:
                is_oa = "Yes"
                oa_status = "License available"
            else:
                is_oa = "N/A"
                oa_status = "N/A"
            download_url = item.get("URL", "N/A")
            cited_by_count = item.get("is-referenced-by-count", "N/A")
            
            registro = {
                "ID": doi,
                "Authors": authors,
                "Authors Year": authors_year,
                "Title": title,
                "Journal": journal,
                "Publication Year": pub_year,
                "Publication Date": pub_date,
                "Abstract": abstract,
                "DOI": doi,
                "Language": language,
                "Is Accepted": is_accepted,
                "Is Published": is_published,
                "Type": type_val,
                "Type Crossref": type_crossref,
                "Indexed In": indexed_in,
                "Is Open Access": is_oa,
                "OA Status": oa_status,
                "Download URL": download_url,
                "Cited By Count": cited_by_count,
                "API": "crossref"
            }
            registro = padroniza_registro(registro)
            records.append(registro)
        return records

    def run_pipeline(self,
                     query: str,
                     max_records: int = None,
                     from_date: str = None,
                     to_date: str = None) -> pd.DataFrame:
        """
        Executa o pipeline completo de busca, paginação, extração e formatação dos dados.
        
        Args:
            query (str): Termo de busca.
            max_records (int, optional): Número máximo de registros a retornar.
        
        Returns:
            pd.DataFrame: Tabela com os resultados padronizados.
        """
        all_records = []
        offset = 0
        while True:
            data = self.fetch_data(
                query,
                offset=offset,
                from_date=from_date,
                to_date=to_date
            )
            records = self.process_data(data)
            if not records:
                break
            all_records.extend(records)
            if max_records and len(all_records) >= max_records:
                all_records = all_records[:max_records]
                break
            total_results = data.get("message", {}).get("total-results", 0)
            offset += self.rows
            if offset >= total_results:
                break
        df = pd.DataFrame(all_records)
        df = df.reindex(columns=STANDARD_COLUMNS)
        return df

# if __name__ == "__main__":
#     query = "machine learning"
#     crossref_api = CrossrefAPI(rows=100)
#     df_resultado = crossref_api.run_pipeline(query=query, max_records=10)
#     print(df_resultado.head())
