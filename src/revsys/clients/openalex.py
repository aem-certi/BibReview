
"""
Módulo para busca de referências de artigos científicos utilizando a API do OpenAlex.

A classe PyAlexFetcher permite a recuperação de metadados de artigos científicos através da API do OpenAlex 
utilizando a biblioteca pyalex. Os dados obtidos são organizados em um DataFrame do Pandas e seguem um formato 
padronizado e igual aos das demais APIs utilizadas para download de metadados (pubmed, plos etc). 

Principais funcionalidades da classe:
- Busca de artigos com base em consultas personalizadas.
- Suporte à filtragem de artigos Open Access.
- Ordenação dos resultados por data de publicação.
- Paginação automática para facilitar a obtenção de múltiplos resultados.
- Retorno dos dados em formato de DataFrame do Pandas.
"""


import pandas as pd
from itertools import chain
from pyalex import Works, config

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

class PyAlexFetcher:
    """
    Classe para buscar referências de artigos no OpenAlex usando pyalex,
    retornando um DataFrame com metadados relevantes padronizados.
    """

    def __init__(self, email: str = None):
        if email:
            config.email = email

    @staticmethod
    def _convert_inverted_index(inverted_index: dict) -> str:
        words = []
        for word, positions in inverted_index.items():
            for pos in positions:
                words.append((pos, word))
        words.sort(key=lambda x: x[0])
        ordered_words = [word for _, word in words]
        return " ".join(ordered_words)

    @staticmethod
    def _process_works(works_list: list) -> pd.DataFrame:
        rows = []
        for w in works_list:
            # Obtém abstract a partir do campo direto ou do índice invertido
            if "abstract" in w and w["abstract"]:
                abstract = w["abstract"]
            elif "abstract_inverted_index" in w and w["abstract_inverted_index"]:
                abstract = PyAlexFetcher._convert_inverted_index(w["abstract_inverted_index"])
            else:
                continue  # Se não houver abstract, ignora o registro

            unique_id = w["id"].split("/")[-1]
            publication_year = w.get("publication_year", "N/A")
            publication_date = w.get("publication_date", "N/A")
            doi = w.get("doi", "N/A")
            language = w.get("language", "N/A")

            # Autores
            authors_list_ = []
            if "authorships" in w:
                authors_list_ = [a["author"]["display_name"] for a in w["authorships"]]
            authors_str = ", ".join(authors_list_) if authors_list_ else "N/A"

            # Gera o campo "Authors Year"
            if authors_list_:
                first_author = authors_list_[0]
                if len(authors_list_) == 1:
                    authors_year = f"{first_author} {publication_year}"
                elif len(authors_list_) == 2:
                    second_author = authors_list_[1]
                    authors_year = f"{first_author} and {second_author} {publication_year}"
                else:
                    authors_year = f"{first_author} et al. {publication_year}"
            else:
                authors_year = f"N/A {publication_year}"

            title = w.get("display_name", "N/A")
            journal = ""
            if w.get("primary_location") and w["primary_location"].get("source"):
                journal = w["primary_location"]["source"].get("display_name", "N/A")

            # Status e download
            is_accepted = w.get("primary_location", {}).get("is_accepted", "N/A")
            is_published = w.get("primary_location", {}).get("is_published", "N/A")
            download_url = w.get("primary_location", {}).get("pdf_url", "") or ""
            best_oa = w.get("best_oa_location")
            if not download_url and best_oa:
                download_url = best_oa.get("pdf_url", "")

            type_ = w.get("type", "N/A")
            type_crossref = w.get("type_crossref", "N/A")
            indexed_in = w.get("indexed_in", [])
            indexed_in_str = ", ".join(indexed_in) if indexed_in else "N/A"

            oa_info = w.get("open_access", {})
            is_oa = oa_info.get("is_oa", False)
            oa_status = oa_info.get("oa_status", "N/A")
            cited_by_count = w.get("cited_by_count", "N/A")

            registro = {
                "ID": unique_id,
                "Authors": authors_str,
                "Authors Year": authors_year,
                "Title": title,
                "Journal": journal,
                "Publication Year": publication_year,
                "Publication Date": publication_date,
                "Abstract": abstract,
                "DOI": doi,
                "Language": language,
                "Is Accepted": is_accepted,
                "Is Published": is_published,
                "Type": type_,
                "Type Crossref": type_crossref,
                "Indexed In": indexed_in_str,
                "Is Open Access": "Yes" if is_oa else "No",
                "OA Status": oa_status,
                "Download URL": download_url,
                "Cited By Count": cited_by_count,
                "API": "openalex"
            }
            registro = padroniza_registro(registro)
            rows.append(registro)

        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        df = df.reindex(columns=STANDARD_COLUMNS)
        return df

    def fetch_references(self, query: str,
                         is_oa: bool = True,
                         sort_order: str = 'desc',
                         per_page: int = 25,
                         n_max: int = 50) -> pd.DataFrame:
        w = Works().search(query)
        if is_oa:
            w = w.filter(is_oa=True)
        if sort_order.lower() in ('desc', 'asc'):
            w = w.sort(publication_date=sort_order.lower())
        pages = w.paginate(per_page=per_page, n_max=n_max)
        all_works = list(chain(*pages))
        df = self._process_works(all_works)
        return df



# ============================
# if __name__ == "__main__":
#     # Inicializa com email (opcional mas recomendado)
#     fetcher = PyAlexFetcher(email="seu-email@exemplo.com")

#     query = '("Interstitial Lung Disease" OR "Pulmonary Fibrosis") AND "Segmentation"'
    
#     df = fetcher.fetch_references(
#         query=query,
#         is_oa=True,       # Filtra Open Access
#         sort_order='desc',
#         per_page=25,
#         n_max=50
#     )
    
#     print("Total de artigos retornados:", len(df))
#     print(df.head(5))
