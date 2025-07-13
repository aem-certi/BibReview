"""
Módulo para consulta de artigos na API IEEE Xplore.
"""

import requests
import pandas as pd
from typing import List, Dict, Any, Optional

# Colunas padronizadas
STANDARD_COLUMNS = [
    "ID", "Authors", "Authors Year", "Title", "Journal", "Publication Year",
    "Publication Date", "Abstract", "DOI", "Language", "Is Accepted", "Is Published",
    "Type", "Type Crossref", "Indexed In", "Is Open Access", "OA Status",
    "Download URL", "Cited By Count", "API"
]

def padroniza_registro(registro: dict) -> dict:
    """Garante que todas as colunas padrão estejam presentes."""
    for col in STANDARD_COLUMNS:
        if col not in registro:
            registro[col] = "N/A"
    return registro

class IeeeXplore:
    """Cliente para buscar artigos via API IEEE Xplore."""
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://ieeexploreapi.ieee.org/api/v1/search/articles"

    def fetch_references(
        self,
        query: str,
        max_records: int = 10,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Busca artigos no IEEE Xplore e retorna DataFrame padronizado.
        """
        params: Dict[str, Any] = {
            'apikey': self.api_key,
            'format': 'json',
            'querytext': query,
            'max_records': max_records,
            'start_record': 1
        }
        if start_year:
            params['start_year'] = start_year
        if end_year:
            params['end_year'] = end_year

        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        data = response.json()
        articles = data.get('articles', [])
        records: List[dict] = []
        for art in articles:
            title = art.get('title', 'N/A')
            abstract = art.get('abstract', 'N/A')
            # Authors
            authors_list = []
            for au in art.get('authors', {}).get('author', []):
                name = au.get('full_name') or au.get('name')
                if name:
                    authors_list.append(name)
            authors_str = ', '.join(authors_list) if authors_list else 'N/A'
            year = str(art.get('publication_year', 'N/A'))
            pub_date = art.get('publication_date', year)
            journal = art.get('publication_title', 'N/A')
            doi = art.get('doi', '')
            pdf_url = art.get('pdf_url', '')
            cited_by = art.get('citation_count', 'N/A')

            registro = {
                'ID': doi if doi else art.get('article_number', f'ieee-{art.get("article_number", idx)}'),
                'Authors': authors_str,
                'Authors Year': f"{authors_str.split(',')[0].split()[-1]} {year}" if authors_str and year != 'N/A' else f'N/A {year}',
                'Title': title,
                'Journal': journal,
                'Publication Year': year,
                'Publication Date': pub_date,
                'Abstract': abstract,
                'DOI': doi,
                'Language': art.get('language', 'N/A'),
                'Is Accepted': 'N/A',
                'Is Published': 'Yes' if year != 'N/A' else 'No',
                'Type': art.get('content_type', 'N/A'),
                'Type Crossref': art.get('content_type', 'N/A'),
                'Indexed In': 'IEEE Xplore',
                'Is Open Access': 'N/A',
                'OA Status': 'N/A',
                'Download URL': pdf_url,
                'Cited By Count': cited_by,
                'API': 'ieee'
            }
            records.append(padroniza_registro(registro))
        df = pd.DataFrame(records)
        df = df.reindex(columns=STANDARD_COLUMNS)
        return df