"""
Módulo para consulta de artigos no Google Scholar usando a biblioteca scholarly.
"""
import pandas as pd
from scholarly import scholarly, ProxyGenerator
import pdb




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

class ScholarClient:
    """Cliente para buscar artigos no Google Scholar."""
    def __init__(self, use_proxy) -> None:
        self.use_proxy = use_proxy
        if self.use_proxy:
            self._setup_proxy()
        # pass
    def _setup_proxy(self) -> None:
        """Configura proxy usando free proxies."""
        try:
            pg = ProxyGenerator()
            # Use FreeProxies - this will automatically fetch free proxies
            success = pg.FreeProxies()
            
            if success:
                scholarly.use_proxy(pg)
                print("Proxy configurado com sucesso usando FreeProxies")
            else:
                print("Falha ao configurar proxy - continuando sem proxy")
                self.use_proxy = False
                
        except Exception as e:
            print(f"Erro ao configurar proxy: {e}")
            print("Continuando sem proxy")
            self.use_proxy = False  
              
    def refresh_proxy(self) -> bool:
        """Atualiza o proxy com uma nova lista de proxies gratuitos."""
        if not self.use_proxy:
            return False
            
        try:
            pg = ProxyGenerator()
            success = pg.FreeProxies()
            
            if success:
                scholarly.use_proxy(pg)
                print("Proxy atualizado com sucesso")
                return True
            else:
                print("Falha ao atualizar proxy")
                return False
                
        except Exception as e:
            print(f"Erro ao atualizar proxy: {e}")
            return False
    
    def disable_proxy(self) -> None:
        """Desabilita o uso de proxy."""
        self.use_proxy = False
        scholarly.use_proxy(None)
        print("Proxy desabilitado")

    def search(self, query: str, max_records: int = 10) -> pd.DataFrame:
        """
        Busca no Google Scholar e retorna DataFrame padronizado.
        """

        
        records = []
        generator = scholarly.search_pubs(query)
        
        for idx, pub in enumerate(generator):
            if idx >= max_records:
                break
            
            title = pub['bib']['title']
            authors = pub['bib']['author']
            if isinstance(authors, list):
                authors_str = ', '.join(authors)
            else:
                authors_str = authors or 'N/A'
            year = str(pub['bib']['pub_year'])
            abstract = pub['bib']['abstract']
            journal = pub['bib']['venue']
            try:
                url = pub['pub_url']
            except:
                pass
            cited_count = pub['num_citations']
            registro = {
                'Authors': authors_str,
                'Authors Year': f"{authors_str.split(',')[0].split()[-1]} {year}" if authors_str and year != 'N/A' else f'N/A {year}',
                'Title': title,
                'Journal': journal,
                'Publication Year': year,
                'Publication Date': year,
                'Abstract': abstract,
                # 'DOI': doi,
                'Language': 'N/A',
                'Is Accepted': 'N/A',
                'Is Published': 'Yes' if year != 'N/A' else 'No',
                'Type': 'scholar',
                'Type Crossref': 'N/A',
                'Indexed In': 'Google Scholar',
                'Is Open Access': 'N/A',
                'OA Status': 'N/A',
                'Download URL': url,
                'Cited By Count': cited_count,
                'API': 'scholar'
            }
            records.append(padroniza_registro(registro))
        df = pd.DataFrame(records)
        df = df.reindex(columns=STANDARD_COLUMNS)
        return df