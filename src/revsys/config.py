"""
Módulo de configuração para o projeto.
Carrega variáveis do arquivo .env, configura loguru e define paths 
de diretórios e endpoints de APIs.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# -----------------------------------------------------------------------------
# 1) Carrega variáveis do .env
# -----------------------------------------------------------------------------
load_dotenv()


# -----------------------------------------------------------------------------
# 2) Configurações de ambiente e sistema
# -----------------------------------------------------------------------------
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

USE_GPU = os.getenv("USE_GPU", "false").lower() == "true"
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "false").lower() == "true"

# -----------------------------------------------------------------------------
# 3) Configurações de busca de artigos
# -----------------------------------------------------------------------------
START_YEAR = int(os.getenv("START_YEAR", "2015"))
END_YEAR = int(os.getenv("END_YEAR", "2025"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "100"))

# -----------------------------------------------------------------------------
# 4) Chaves de API e e-mails
# -----------------------------------------------------------------------------
LANGUAGE = os.getenv("LANGUAGE", "en")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY", "")
SPRINGER_API_KEY = os.getenv("SPRINGER_API_KEY", "")
# Contato para OpenAlex queries
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "")
# Chave de API para PubMed (NCBI E-utilities)
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
# Chave de API para IEEE Xplore
IEEE_API_KEY = os.getenv("IEEE_API_KEY", "")

# -----------------------------------------------------------------------------
# 6) Configurações de LLM e embeddings
# -----------------------------------------------------------------------------
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4.1-mini")
GENERATION_TEMPERATURE = float(os.getenv("GENERATION_TEMPERATURE", "0.3"))
GENERATION_P = float(os.getenv("GENERATION_P", "1.0"))
RESPONSE_FORMAT = os.getenv("RESPONSE_FORMAT", "text")

# -----------------------------------------------------------------------------
# 7) Definição de PATHs
# -----------------------------------------------------------------------------
# PROJ_ROOT assume que o config.py está em "meu_projeto/config.py", e queremos
# subir 1 nível para a raiz. Ajuste se necessário para o seu caso.
PROJ_ROOT = Path(__file__).resolve().parents[1]

# As pastas podem ser definidas no .env ou valores fixos aqui
DATA_SUBFOLDER = os.getenv("DATA_SUBFOLDER", "data")
LOGS_SUBFOLDER = os.getenv("LOGS_SUBFOLDER", "logs")
LLM_SUBFOLDER = os.getenv("LLM_SUBFOLDER", "llm")
REPORTS_SUBFOLDER = os.getenv("REPORTS_SUBFOLDER", "reports")
FIGURES_SUBFOLDER = os.getenv("FIGURES_SUBFOLDER", "figures")

# Diretórios derivados
DATA_DIR = PROJ_ROOT / DATA_SUBFOLDER
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

LOGS_DIR = PROJ_ROOT / LOGS_SUBFOLDER
LLM_DIR = PROJ_ROOT / LLM_SUBFOLDER
REPORTS_DIR = PROJ_ROOT / REPORTS_SUBFOLDER
FIGURES_DIR = REPORTS_DIR / FIGURES_SUBFOLDER

_ALL_FOLDERS = [
    DATA_DIR, RAW_DATA_DIR, INTERIM_DATA_DIR, PROCESSED_DATA_DIR,
    LOGS_DIR, LLM_DIR, REPORTS_DIR, FIGURES_DIR
]
# Criar as pastas de dados e logs
for folder in _ALL_FOLDERS:
    folder.mkdir(parents=True, exist_ok=True)

# Cache de requisições HTTP (usando requests-cache)
CACHE_EXPIRE = int(os.getenv("CACHE_EXPIRE", "3600"))  # segundos
if CACHE_ENABLED:
    try:
        import requests_cache
        cache_path = PROJ_ROOT / 'cache' / 'http_cache'
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        requests_cache.install_cache(str(cache_path), expire_after=CACHE_EXPIRE)
        logger.info(f"HTTP cache habilitado em {cache_path}, expira em {CACHE_EXPIRE} segundos")
    except ImportError:
        logger.warning("requests-cache não instalado; caching HTTP desabilitado")


# -----------------------------------------------------------------------------
# 8) Configuração de logging (usando loguru)
# -----------------------------------------------------------------------------
# Remove qualquer config default (opcional)
logger.remove()

# Formatação de log
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Console
logger.add(
    sink=lambda msg: print(msg, end=""),
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    enqueue=True  # recomendado para multithread
)

# Arquivo de log (com rotação de 10 MB, compressão em zip)
LOG_FILE_PATH = LOGS_DIR / "app.log"
logger.add(
    str(LOG_FILE_PATH),
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    rotation="10 MB",
    compression="zip",
    enqueue=True
)

# Logs iniciais para inspecionar configurações
logger.info(f"ENVIRONMENT={ENVIRONMENT}, LOG_LEVEL={LOG_LEVEL}, PROJ_ROOT={PROJ_ROOT}")
logger.info(f"DATA_DIR={DATA_DIR}, LOGS_DIR={LOGS_DIR}, LLM_DIR={LLM_DIR}")
logger.info("Config carregado com sucesso.")


# -----------------------------------------------------------------------------
# 9) Funções auxiliares
# -----------------------------------------------------------------------------
def init_config() -> None:
    """
    Função opcional a ser chamada no início do projeto para
    garantir que este módulo seja carregado e todas as pastas
    tenham sido criadas.
    """
    logger.info("init_config() chamado. Configurações já foram carregadas.")
