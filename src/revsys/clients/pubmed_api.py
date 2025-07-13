"""
pubmed_api.py
Busca de artigos no PubMed usando E-utilities (esearch + efetch).
Retorna um DataFrame padronizado.

Principais funcionalidades da classe:
- Busca de artigos com base em consultas / query. 
- Extração e formatação dos dados em um formato estruturado.
- Suporte à paginação automática para obtenção de múltiplos resultados.
- Retorno dos dados em formato de DataFrame do Pandas, com colunas padronizadas.
"""

import requests
import pandas as pd
import logging
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree
from revsys.http_retry import retry_on_fail

STANDARD_COLUMNS = [
    "ID", "Authors", "Authors Year", "Title", "Journal", "Publication Year",
    "Publication Date", "Abstract", "DOI", "Language", "Is Accepted", "Is Published",
    "Type", "Type Crossref", "Indexed In", "Is Open Access", "OA Status", "Download URL",
    "Cited By Count", "API"
]

def padroniza_registro(registro: dict) -> dict:
    # Preenche as colunas padrão se não estiverem presentes
    for coluna in STANDARD_COLUMNS:
        if coluna not in registro:
            registro[coluna] = "N/A"
    return registro

class PubMedAPI:
    """
    Classe para buscar artigos no PubMed usando E-utilities do NCBI (esearch + efetch).
    Pode retornar uma quantidade limitada de artigos ou todos os artigos disponíveis
    para a query, conforme necessidade.
    """

    def __init__(
        self,
        api_key: str = "",
        tool: str = "MyTool",
        email: str = "myemail@example.com",
        log_level: int = logging.INFO
    ):
        """
        Inicializa a classe PubMedAPI.
        Você pode incluir api_key para cumprir boas práticas do NCBI (parâmetro 'api_key').
        Ferramenta e e-mail para identificação junto ao servidor NCBI.

        Args:
            api_key (str, optional): Chave de API do PubMed (opcional).
            tool (str, optional): Nome da ferramenta (para o NCBI). Padrão "MyTool".
            email (str, optional): E-mail de contato. Padrão "myemail@example.com".
            log_level (int, optional): Nível de logging. Padrão logging.INFO.
        """
        self.api_key = api_key
        self.tool = tool
        self.email = email

        logging.basicConfig(level=log_level)
        self.logger = logging.getLogger(__name__)

    def search(
        self,
        query: str,
        retmax: Optional[int] = 10000,
        fetch_all: bool = False,
        from_date: str = None,
        to_date: str = None
    ) -> pd.DataFrame:
        """
        Realiza a busca no PubMed para a query especificada e retorna um DataFrame
        padronizado com os artigos encontrados. Possui dois modos de operação:
        - Modo padrão (fetch_all=False): retorna até 'retmax' artigos.
        - Modo "todos os resultados" (fetch_all=True): faz paginação para retornar
          todos os artigos encontrados.

        Observação: Dependendo da query, o PubMed pode ter limites práticos
        (e.g., 100.000 resultados). Use fetch_all com cuidado.

        Args:
            query (str): Termo de busca (por ex.: "machine learning").
            retmax (int, optional): Máximo de artigos a retornar se fetch_all=False.
                                    Se fetch_all=True, esse parâmetro é ignorado.
                                    Padrão 10.
            fetch_all (bool, optional): Se True, retorna todos os resultados
                                        disponíveis para a query. Padrão False.

        Returns:
            pd.DataFrame: DataFrame com colunas padronizadas (ID, Unique ID,
                          Title, Abstract, etc.).
        """
        # Armazena filtros de data para a busca (YYYY/MM/DD no formato aceito)
        self.datetype = None
        if from_date or to_date:
            self.datetype = 'pdat'
        self.mindate = from_date
        self.maxdate = to_date
        # Se fetch_all for True, descobrimos o total de resultados e trazemos tudo.
        if fetch_all:
            total_count = self._get_total_count(query)
            self.logger.info(f"Total de resultados encontrados: {total_count}")
            all_pmids = self._fetch_all_pmids(query, total_count)
            # EFetch dos PMIDs em lotes
            raw_entries = []
            chunk_size = 200  # Pode ajustar conforme necessidade
            for start in range(0, len(all_pmids), chunk_size):
                subset = all_pmids[start : start + chunk_size]
                self.logger.info(f"Buscando detalhes de {len(subset)} artigos...")
                raw_entries.extend(self._fetch_details(subset))
        else:
            # Modo normal: busca retmax artigos (esearch + efetch de uma vez só)
            if retmax is None:
                retmax = 10  # fallback
            self.logger.info(f"Buscando até {retmax} artigos para a query '{query}'...")
            pmid_list = self._fetch_pmids(query, retmax=retmax, retstart=0)
            if not pmid_list:
                return pd.DataFrame()
            raw_entries = self._fetch_details(pmid_list)

        # Converte lista de dicionários para DataFrame
        df = self._parse_data(raw_entries)
        return df

    @retry_on_fail
    def _get_total_count(self, query: str) -> int:
        """
        Obtém o número total de artigos existentes para a query no PubMed.

        Args:
            query (str): Termo de busca.

        Returns:
            int: Número total de resultados para a query.
        """
        esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params_esearch = {
            "db": "pubmed",
            "term": query,
            "retmode": "xml",
            "tool": self.tool,
            "email": self.email,
        }
        # Filtros de data
        if getattr(self, 'datetype', None):
            params_esearch['datetype'] = self.datetype
        if getattr(self, 'mindate', None):
            params_esearch['mindate'] = self.mindate
        if getattr(self, 'maxdate', None):
            params_esearch['maxdate'] = self.maxdate
        if self.api_key:
            params_esearch["api_key"] = self.api_key

        resp_esearch = requests.get(esearch_url, params=params_esearch)
        resp_esearch.raise_for_status()
        root_esearch = ElementTree.fromstring(resp_esearch.content)

        count_elem = root_esearch.find(".//Count")
        if count_elem is not None and count_elem.text.isdigit():
            return int(count_elem.text)
        return 0

    @retry_on_fail
    def _fetch_all_pmids(self, query: str, total_count: int) -> List[str]:
        """
        Faz paginação para coletar todos os PMIDs existentes para a query.

        Args:
            query (str): Termo de busca.
            total_count (int): Número total de resultados a coletar.

        Returns:
            List[str]: Lista de PMIDs.
        """
        all_pmids = []
        step = 10000  # Ajuste conforme limites e desempenho
        current_start = 0

        while current_start < total_count:
            self.logger.info(f"Coletando PMIDs de {current_start} até {current_start + step - 1}...")
            pmid_batch = self._fetch_pmids(query, retmax=step, retstart=current_start)
            if not pmid_batch:
                break
            all_pmids.extend(pmid_batch)
            current_start += step

            # Se por algum motivo vier menos PMIDs do que o step, chegamos ao fim
            if len(pmid_batch) < step:
                break

        return all_pmids

    @retry_on_fail
    def _fetch_pmids(self, query: str, retmax: int, retstart: int) -> List[str]:
        """
        Busca PMIDs via ESearch para a query especificada.

        Args:
            query (str): Termo de busca.
            retmax (int): Máximo de artigos a retornar nesta chamada.
            retstart (int): Offset inicial para paginação.

        Returns:
            List[str]: Lista de PMIDs obtidos.
        """
        esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params_esearch = {
            "db": "pubmed",
            "term": query,
            "retmax": retmax,
            "retstart": retstart,
            "retmode": "xml",
            "tool": self.tool,
            "email": self.email,
        }
        # Filtros de data
        if getattr(self, 'datetype', None):
            params_esearch['datetype'] = self.datetype
        if getattr(self, 'mindate', None):
            params_esearch['mindate'] = self.mindate
        if getattr(self, 'maxdate', None):
            params_esearch['maxdate'] = self.maxdate
        if self.api_key:
            params_esearch["api_key"] = self.api_key

        resp_esearch = requests.get(esearch_url, params=params_esearch)
        resp_esearch.raise_for_status()
        root_esearch = ElementTree.fromstring(resp_esearch.content)

        # Extrai IDs
        id_list = [elem.text for elem in root_esearch.findall(".//Id")]
        return id_list

    @retry_on_fail
    def _fetch_details(self, pmid_list: List[str]) -> List[Dict[str, Any]]:
        """
        Dado um lote de PMIDs, obtém os detalhes (título, autores, abstract, etc.) via EFetch.

        Args:
            pmid_list (List[str]): Lista de PMIDs.

        Returns:
            List[Dict[str, Any]]: Lista de dicionários com metadados de cada artigo.
        """
        if not pmid_list:
            return []

        efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params_efetch = {
            "db": "pubmed",
            "id": ",".join(pmid_list),
            "retmode": "xml",
            "tool": self.tool,
            "email": self.email,
        }
        if self.api_key:
            params_efetch["api_key"] = self.api_key

        resp_efetch = requests.get(efetch_url, params=params_efetch)
        resp_efetch.raise_for_status()
        root_efetch = ElementTree.fromstring(resp_efetch.content)

        raw_entries = []
        for article_elem in root_efetch.findall(".//PubmedArticle"):
            item = self._parse_pubmed_article(article_elem)
            raw_entries.append(item)

        return raw_entries

    def _parse_data(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Converte a lista de dicionários do PubMed em DataFrame padronizado.
        """
        records = []
        for entry in raw_data:
            pmid = entry.get("pmid", "")
            doi = entry.get("doi", "")
            # "ID": se houver DOI, usar esse. Caso contrário, fallback para PMID
            final_id = doi if doi else pmid

            # "Unique ID" não será incluído aqui, pois nosso padrão é diferente.
            # Monta referência no estilo Vancouver (exemplo)
            reference_vancouver = self._create_vancouver_style(entry)

            authors_str = entry.get("authors_str", "")
            authors_year = entry.get("authors_year", "")
            title_str = entry.get("title", "")
            journal = entry.get("journal", "")
            volume = entry.get("volume", "")
            issue = entry.get("issue", "")
            pages = entry.get("pages", "")
            pub_year = entry.get("year", "")
            pub_date = entry.get("publication_date", "")
            abstract = entry.get("abstract", "")

            # Heurística para "Is Published" e "Status"
            pub_status = entry.get("publication_status", "").lower()
            if pub_status in ("epublish", "ppublish", "pubmed", "medline"):
                is_published = "Yes"
            else:
                is_published = "No"

            # "Is Open Access" e "OA Status"
            is_oa = entry.get("is_oa", False)
            oa_status = "PMC - Possibly OA" if is_oa else "N/A"

            download_url = entry.get("download_url", "")

            registro = {
                "ID": final_id,
                "Authors": authors_str,
                "Authors Year": authors_year,
                "Title": title_str,
                "Journal": journal,
                "Publication Year": pub_year,
                "Publication Date": pub_date,
                "Abstract": abstract,
                "DOI": doi,
                "Language": entry.get("language", "N/A"),
                "Is Accepted": "N/A",   # Campo não fornecido na API
                "Is Published": is_published,
                "Type": "article",      # Pode ajustar conforme necessário
                "Type Crossref": entry.get("contentType", "N/A"),
                "Indexed In": "PubMed",  # Informação fixa para PubMed
                "Is Open Access": "Yes" if is_oa else "No",
                "OA Status": oa_status,
                "Download URL": download_url,
                "Cited By Count": 0,     # PubMed não fornece contagem de citações
                "API": "pubmed"
            }

            # Aplica a padronização: garante que todas as colunas estejam presentes
            registro = padroniza_registro(registro)
            records.append(registro)

        df = pd.DataFrame(records)
        # Reordena as colunas conforme a lista padrão
        df = df.reindex(columns=STANDARD_COLUMNS)
        return df

    # =========================================================================
    # Métodos auxiliares
    # =========================================================================

    def _parse_pubmed_article(self, article_elem: ElementTree.Element) -> Dict[str, Any]:
        """
        Faz parse de um elemento <PubmedArticle> do XML do EFetch,
        extraindo PMID, DOI, título, autores, abstract, etc.

        Args:
            article_elem (ElementTree.Element): Elemento XML representando um artigo PubMed.

        Returns:
            Dict[str, Any]: Dicionário com campos básicos que depois serão convertidos em DataFrame.
        """
        pmid_elem = article_elem.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""

        article_title_elem = article_elem.find(".//ArticleTitle")
        title = article_title_elem.text if article_title_elem is not None else ""

        journal_elem = article_elem.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else ""

        volume_elem = article_elem.find(".//JournalIssue/Volume")
        issue_elem = article_elem.find(".//JournalIssue/Issue")
        pages_elem = article_elem.find(".//Pagination/MedlinePgn")

        volume = volume_elem.text if volume_elem is not None else ""
        issue = issue_elem.text if issue_elem is not None else ""
        pages = pages_elem.text if pages_elem is not None else ""

        pub_year, publication_date = self._extract_pub_date(article_elem)

        # DOI
        doi = ""
        for article_id in article_elem.findall(".//ArticleIdList/ArticleId"):
            if article_id.attrib.get("IdType", "").lower() == "doi":
                doi = article_id.text
                break

        # Autores
        authors_list = []
        authors_elems = article_elem.findall(".//AuthorList/Author")
        for author in authors_elems:
            last = author.find("LastName")
            fore = author.find("ForeName")
            coll = author.find("CollectiveName")
            if last is not None and fore is not None:
                authors_list.append(f"{fore.text} {last.text}")
            elif coll is not None:
                authors_list.append(coll.text)

        authors_str = ", ".join(authors_list) if authors_list else ""
        authors_year = self._make_authors_year(authors_list, pub_year)

        # Abstract
        abstracts = []
        abstract_elems = article_elem.findall(".//Abstract/AbstractText")
        for ab_elem in abstract_elems:
            if ab_elem.text:
                abstracts.append(ab_elem.text)
        abstract_text = " ".join(abstracts).strip() if abstracts else ""

        # Idioma
        lang_elem = article_elem.find(".//Article/Language")
        language = lang_elem.text if lang_elem is not None else ""

        # Verifica se existe PMCID (PubMed Central) => possivelmente OA
        pmc_id = ""
        publication_status = ""
        for article_id in article_elem.findall(".//ArticleIdList/ArticleId"):
            id_type = article_id.attrib.get("IdType", "").lower()
            if id_type == "pmc":
                pmc_id = article_id.text
            if id_type == "pubstatus":
                publication_status = article_id.text

        # Is OA se tiver PMC
        is_oa = bool(pmc_id)

        # Download URL: se tiver PMC, gera link
        download_url = ""
        if pmc_id:
            if not pmc_id.startswith("PMC"):
                pmc_id = "PMC" + pmc_id
            download_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"
        elif doi:
            download_url = f"https://doi.org/{doi}"

        return {
            "pmid": pmid,
            "doi": doi,
            "title": title,
            "journal": journal,
            "volume": volume,
            "issue": issue,
            "pages": pages,
            "year": pub_year,
            "publication_date": publication_date,
            "authors_str": authors_str,
            "authors_year": authors_year,
            "abstract": abstract_text,
            "language": language,
            "is_oa": is_oa,
            "download_url": download_url,
            "publication_status": publication_status,
        }

    def _extract_pub_date(self, article_elem: ElementTree.Element) -> (str, str):
        """
        Extrai o ano e a data completa (AAAA-MM-DD) do trecho de PubDate,
        usando heurística para Month, Day, etc.

        Args:
            article_elem (ElementTree.Element): Elemento do artigo PubMed.

        Returns:
            (str, str): Uma tupla (pub_year, publication_date), por exemplo ("2023", "2023-05-12").
        """
        pub_year = ""
        publication_date = ""

        pubdate_elem = article_elem.find(".//JournalIssue/PubDate")
        if pubdate_elem is not None:
            # Tenta Year, Month, Day
            year_elem = pubdate_elem.find("Year")
            if year_elem is not None:
                pub_year = year_elem.text or ""
            else:
                # Tenta MedlineDate (ex.: "2023 Jan-Mar")
                medline_elem = pubdate_elem.find("MedlineDate")
                if medline_elem is not None and medline_elem.text:
                    pub_year = medline_elem.text[:4]

            month_elem = pubdate_elem.find("Month")
            day_elem = pubdate_elem.find("Day")

            mm = ""
            if month_elem is not None and month_elem.text:
                mm = self._month_to_number(month_elem.text)

            dd = day_elem.text if day_elem is not None else ""

            if pub_year and mm and dd.isdigit():
                publication_date = f"{pub_year}-{mm}-{dd}"
            elif pub_year and mm:
                publication_date = f"{pub_year}-{mm}"
            else:
                publication_date = pub_year

        return pub_year, publication_date

    def _month_to_number(self, month_str: str) -> str:
        """
        Converte algo como 'Jan' -> '01', 'Feb' -> '02'.
        Se já for número, mantém. Caso não reconheça, retorna string vazia.

        Args:
            month_str (str): Nome do mês (por ex.: "Jan", "Feb", "12").

        Returns:
            str: Mês em formato "MM" ou "" se não reconhecido.
        """
        month_map = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05",
            "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10",
            "Nov": "11", "Dec": "12"
        }
        if month_str in month_map:
            return month_map[month_str]
        if month_str.isdigit():
            return f"{int(month_str):02d}"
        return ""

    def _make_authors_year(self, authors_list: List[str], year: str) -> str:
        """
        Gera o campo 'Authors Year' no estilo 'Silva et al. 2023'.

        Args:
            authors_list (List[str]): Lista de autores ["João Silva", "Maria Souza", ...].
            year (str): Ano de publicação.

        Returns:
            str: Exemplo: "Silva et al. 2023".
        """
        if not authors_list:
            return f"Unknown {year}"

        first_author_last = authors_list[0].split()[-1]
        if len(authors_list) == 1:
            return f"{first_author_last} {year}"
        else:
            return f"{first_author_last} et al. {year}"

    def _create_vancouver_style(self, entry: Dict[str, Any]) -> str:
        """
        Monta referência no estilo Vancouver:
        'Authors. Title. Journal. Year;Volume(Issue):Pages.'

        Args:
            entry (Dict[str, Any]): Dados do artigo.

        Returns:
            str: Referência no formato Vancouver.
        """
        authors = entry.get("authors_str", "")
        title = entry.get("title", "")
        journal = entry.get("journal", "")
        year = entry.get("year", "")
        volume = entry.get("volume", "")
        issue = entry.get("issue", "")
        pages = entry.get("pages", "")

        ref = f"{authors}. {title}. {journal}. {year}"
        if volume:
            ref += f";{volume}"
            if issue:
                ref += f"({issue})"
            if pages:
                ref += f":{pages}."
            else:
                ref += "."
        else:
            ref += "."

        return ref


# if __name__ == "__main__":
#
#     api = PubMedAPI(api_key="", tool="TestTool", email="test@example.com")
#     query_test = "machine learning"
#
#     df_limited = api.search(query=query_test, retmax=5, fetch_all=False)
#     print(f"Coletados {len(df_limited)} artigos (modo limitado).")
