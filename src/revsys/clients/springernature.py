"""
Script para coletar, padronizar e estruturar metadados de artigos científicos 
a partir da API Springer Nature. 

Este script define uma classe `SpringerNature` que:
1. Consulta a API Springer Nature com uma query de busca personalizada;
2. Trata falhas de conexão e faz tentativas automáticas em caso de erro (com foco em erros 503 e 504);
3. Processa os dados retornados pela API e extrai campos relevantes;
4. Padroniza os registros conforme um modelo comum de colunas (definido em `STANDARD_COLUMNS`);
5. Retorna os resultados organizados como um `pandas.DataFrame`.
"""

import os
import datetime
import requests
import pandas as pd
import time
from revsys.config import logger

# Logging via revsys.config.logger


# ---------------------------------------------------------
# Define as colunas padrão que queremos para todos os registros
STANDARD_COLUMNS = [
    "ID", "Authors", "Authors Year", "Title", "Journal", "Publication Year",
    "Publication Date", "Abstract", "DOI", "Language", "Is Accepted", "Is Published",
    "Type", "Type Crossref", "Indexed In", "Is Open Access", "OA Status",
    "Download URL", "Cited By Count", "API"
]

def padroniza_registro(registro: dict) -> dict:
    """
    Garante que todos os campos esperados existam no registro.
    Se algum campo estiver ausente, ele será preenchido com 'N/A'.
    """
    for coluna in STANDARD_COLUMNS:
        if coluna not in registro:
            registro[coluna] = "N/A"
    return registro

# ---------------------------------------------------------
class SpringerNature:
    def __init__(self, api_key: str, base_url: str = "https://api.springernature.com/meta/v2/json"):
        """
        Inicializa a classe com a chave da API e a URL base da API Springer.
        """
        self.api_key = api_key
        self.base_url = base_url

    def fetch_data(self, query_params: dict) -> dict:
        """
        Realiza a requisição à API Springer com os parâmetros fornecidos.
        Tenta múltiplas vezes em caso de erros temporários (ex: 503).
        """
        params = query_params.copy()
        params['api_key'] = self.api_key
        max_retries = 3  
        delay = 10       
        for attempt in range(max_retries):
            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                logger.info(f"Requisição bem-sucedida na tentativa {attempt + 1}.")
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code in (503, 504):
                    logger.warning(
                        f"Erro {response.status_code}. Tentativa {attempt + 1}/{max_retries}. "
                        f"Aguardando {delay * (attempt + 1)}s.")
                    time.sleep(delay * (attempt + 1))
                    continue
                else:
                    logger.error(f"HTTPError: {e} - Status Code: {response.status_code}")
                    raise
            except requests.exceptions.Timeout as e:
                logger.error(
                    f"Timeout: {e}. Tentativa {attempt + 1}/{max_retries}. "
                    f"Aguardando {delay * (attempt + 1)}s.")
                time.sleep(delay * (attempt + 1))
                continue
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"RequestException: {e}. Tentativa {attempt + 1}/{max_retries}. "
                    f"Aguardando {delay * (attempt + 1)}s.")
                time.sleep(delay * (attempt + 1))
                continue
        raise Exception(f"Falha na consulta após {max_retries} tentativas devido a timeout ou outros erros.")

    def _format_authors_year(self, creators: list, publication_date: str) -> str:
        """
        Formata os autores e o ano de publicação: 
        'Silva 2023' ou 'Silva and Moura 2023' ou 'Silva et al. 2023'.
        """
        year = publication_date.split("-")[0] if publication_date else ""
        surnames = []
        for creator in creators:
            nome_completo = creator.get("creator", "")
            if "," in nome_completo:
                sobrenome = nome_completo.split(",")[0].strip()
            else:
                sobrenome = nome_completo.strip()
            surnames.append(sobrenome)
        if not surnames:
            return year
        elif len(surnames) == 1:
            return f"{surnames[0]} {year}"
        elif len(surnames) == 2:
            return f"{surnames[0]} and {surnames[1]} {year}"
        else:
            return f"{surnames[0]} et al. {year}"

    def process_data(self, data: dict) -> list:
        """
        Processa os dados brutos da API e retorna uma lista de registros padronizados.
        """
        results = []
        records = data.get('records', [])
        for rec in records:
            creators = rec.get('creators', [])
            authors_str = ", ".join([creator.get("creator", "") for creator in creators]) if creators else "N/A"
            pub_date = rec.get('publicationDate', "N/A")
            authors_year = self._format_authors_year(creators, pub_date) if pub_date != "N/A" else "N/A"
            publication_year = pub_date.split("-")[0] if pub_date != "N/A" and "-" in pub_date else "N/A"
            url_list = rec.get('url', [])
            download_url = url_list[0].get("value") if url_list and isinstance(url_list, list) and "value" in url_list[0] else "N/A"
            openaccess = rec.get('openaccess', "false")
            is_oa = True if str(openaccess).lower() == "true" else False

            registro = {
                "ID": rec.get('doi', "N/A"),
                "Authors": authors_str,
                "Authors Year": authors_year,
                "Title": rec.get('title', "N/A"),
                "Journal": rec.get('publicationName', "N/A"),
                "Publication Year": publication_year,
                "Publication Date": pub_date,
                "Abstract": rec.get('abstract', "N/A"),
                "DOI": rec.get('doi', "N/A"),
                "Language": rec.get('language', "N/A"),
                "Is Accepted": "N/A",
                "Is Published": "N/A",
                "Type": rec.get('contentType', "N/A"),
                "Type Crossref": rec.get('contentType', "N/A"),
                "Indexed In": "SpringerNature",
                "Is Open Access": "Yes" if is_oa else "No",
                "OA Status": "N/A",
                "Download URL": download_url,
                "Cited By Count": "N/A",
                "API": "springernature"
            }
            registro = padroniza_registro(registro)
            results.append(registro)
        return results

    def to_dataframe(self, records: list) -> pd.DataFrame:
        """
        Converte a lista de registros padronizados para um DataFrame com colunas fixas.
        """
        df = pd.DataFrame(records)
        df = df.reindex(columns=STANDARD_COLUMNS)
        return df

    def run_pipeline(self, q: str, p: int = 25, from_date: str = None, to_date: str = None, max_records: int = None) -> pd.DataFrame:
        """
        Executa o pipeline de busca, paginação e retorno dos dados em DataFrame.
        - q: termo de busca
        - p: número de registros por página
        - from_date / to_date: filtro de intervalo de datas (YYYY-MM-DD)
        - max_records: número máximo total de registros a coletar
        """
        all_records = []
        # Parâmetros iniciais
        params = {"q": q, "p": p}
        if from_date:
            params["dateFrom"] = from_date
        if to_date:
            params["dateTo"] = to_date

        next_page = None
        while True:
            # Buscar página atual
            if next_page:
                resp = requests.get(next_page, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            else:
                data = self.fetch_data(params)

            records = self.process_data(data)
            if not records:
                break
            all_records.extend(records)

            # Respeitar limite total
            if max_records is not None and len(all_records) >= max_records:
                all_records = all_records[:max_records]
                break

            # Próxima página via nextPage do JSON
            next_page = data.get("nextPage")
            if not next_page:
                # Se menos que page size, encerra
                if len(records) < p:
                    break
                # Fallback: paginar manualmente via parâmetro s
                start = params.get("s", 1)
                params["s"] = start + p
            # Continua loop
        return self.to_dataframe(all_records)
