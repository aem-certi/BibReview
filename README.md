![BibReview Logo](imgs/BibReview_Logo.png)

# Projeto de Revisão Sistemática Automatizada com LLM e PRISMA

Uma ferramenta em Python para conduzir revisões sistemáticas de literatura científica seguindo o protocolo PRISMA, integrando busca automatizada, triagem semântica e análise com modelos de linguagem.


## Funcionalidades

- **Busca de artigos** em múltiplas fontes (padrão: arXiv, Crossref, OpenAlex; suportadas PLOS, PubMed, Scopus, SpringerNature, Scholar e IEEE).
- **Triagem semântica** com pré-filtragem baseada em embeddings (`--incl-key`, `--excl-key`, thresholds) e fallback sem chave de API.
- **Revisão e resumo** de artigos com LLM (fallback sem chave de API).
- **Download automático de PDFs** e extração de texto completo (PDF, XML/JATS).
- **Orquestração de pipeline** completa (`search`, `triage`, `review`, `fetch-fulltext` e geração de fluxograma PRISMA) via CrewAI ou CLI.
- **Configuração automática** de diretórios (dados, cache, logs, relatórios) e logging com Loguru.
- **Cache HTTP opcional** com `requests-cache` para acelerar requisições.


## Requisitos

- Python ≥ 3.8 
- Git
- (opcional) [uv](https://astral.sh/uv) (gerenciador de ambientes e pacotes)
- (opcional) `dot` do Graphviz (para geração de fluxogramas PRISMA)


## Instalação

```bash
# Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# ou via pip
echo pip install uv | bash

# Clonar o repositório e entrar na pasta
git clone git@bitbucket.org:certi_repos/bibreview.git
cd bibreview

# Criar e ativar ambiente virtual
uv venv
source .venv/bin/activate

# Instalar dependências
uv pip install -r requirements.txt
uv pip install -e .
```

## Configuração

1. Copie `.env.example` para `.env`.
2. Preencha as chaves de API em `.env`.


## Uso da CLI

Execute a ferramenta pelo comando `revsys` seguido de subcomandos e opções:

### 1. `revsys search`
Busca artigos e exporta metadados para CSV.
```bash
revsys search \
  --query "machine learning" \
  --sources crossref,openalex \
  --from-date 2022-01-01 \
  --to-date 2023-01-01 \
  --max-records 100 \
  --output resultados.csv
```

* Obs 1 . Para buscar com três fontes ou mais, utilize o -s antes de cada fonte. Ex. -s crossref -s arvix -s openalex
* Obs 2 . Existem limites para busca nas APIs de bases fechadas.
* Obs 3 . A busca no scholar possui alguns bugs de proxy. Sugirimos utilizar outros métodos por enquanto. 

### 2. `revsys triage`
Triagem assistida por IA dos artigos encontrados.
```bash
revsys triage \
  --query "machine learning" \
  --input resultados.csv \
  --output triaged.csv
```

### 3. `revsys review`
Revisão e resumo com LLM dos artigos triados.
```bash
revsys review \
  --input triaged.csv \
  --output review.csv
```

### 4. `revsys download-pdfs`
Download automático de PDFs.
```bash
revsys download-pdfs \
  --input triaged.csv \
  --failure-output failed_downloads.csv \
  --output-dir pdfs/
```

### 5. `revsys fetch-fulltext`
Extrai texto completo de PDFs/XML para RAG.
```bash
revsys fetch-fulltext \
  --input triaged.csv \
  --output-dir fulltexts/ \
  --output triaged_fulltext.json
```

### 6. `revsys prisma-diagram`
Gera fluxograma visual PRISMA.
```bash
revsys prisma-diagram \
  --identified 200 \
  --pretriage 150 \
  --triaged 100 \
  --fulltext 80 \
  --output prisma_flowchart.png
```

## Fluxo de Trabalho

1. **Definir diretrizes** (pergunta de pesquisa, critérios de inclusão/exclusão, query) usando notebook de apoio.
2. **Buscar** metadados em várias bases.
3. **Pré-triagem semântica** (TF-IDF, embeddings).
4. **Triagem com LLM** (GPT-4o ou fallback).
5. **Download e extração** de full-text (PDF/XML).
6. **Revisão com RAG** e geração de seções estruturadas.
7. **Gerar relatório** e fluxograma PRISMA.

## Estrutura do Projeto



## Uso da CLI

Após a instalação, utilize o comando `revsys`:

```bash
revsys search \
  --query '"lung" AND ("segmentation" OR "deep learning" OR "machine learning")' \
  --sources crossref \
  --from-date 2022-01-01 \
  --to-date 2023-01-01 \
  --max-records 50 \
  --output resultados.csv
```

Opções principais:
- `--query` (obrigatório): termo de busca de documentos cientificos. 
-- `--sources`: fontes a consultar. Valores possíveis:
  `arxiv`, `crossref`, `openalex`, `plos`, `pubmed`, `scopus`,
  `springernature`, `scholar`, `ieee`.
  Padrão: `arxiv`, `crossref`, `openalex`.
- `--from-date` / `--to-date`: filtros de data (YYYY-MM-DD) para APIs que suportam.
- `--max-records`: máximo de registros por fonte.
- `--output`: caminho do CSV de saída.

### revsys triage
Triagem assistida por IA dos artigos pesquisados.

```bash
revsys triage \
  --query '"lung" AND ("segmentation" OR "deep learning" OR "machine learning")' \
  --input resultados.csv \
  --output triaged.csv
```

Opções:
- `--query`, `-q`: pergunta de pesquisa.
- `--input`, `-i`: CSV de input (search).
- `--output`, `-o`: CSV de output (triaged).

### revsys review
Revisão e resumo assistido por LLM dos artigos triados.

```bash
revsys review \
  --input triaged.csv \
  --output review.csv
```

Opções:
- `--input`, `-i`: CSV de input (triaged).
- `--output`, `-o`: CSV ou TXT de output (resumos).

### revsys download-pdfs
Download automático de PDFs dos artigos listados.

```bash
revsys download-pdfs \
  --input triaged.csv \
  --output-dir pdfs/
```

Opções:
- `--input`, `-i`: CSV de input com coluna `Download URL`.
- `--output-dir`, `-d`: diretório para salvar PDFs.

### revsys fetch-fulltext
Download de PDFs/XML e extração de texto completo.

```bash
revsys fetch-fulltext \
  --input triaged.csv \
  --output-dir fulltexts/ \
  --output triaged_fulltext.json
```
Opções:
- `--input`, `-i`: CSV de input com colunas `DOI` ou `Download URL`.
- `--output-dir`, `-d`: diretório para salvar PDFs/XML e texto extraído.
- `--output`, `-o`: arquivo JSON de saída com conteúdo completo.

### revsys run
Orquestra pipeline completo:
- define diretrizes (pergunta, critérios e query)
- busca refinada via `search_query`
- triagem assistida por IA
- revisão de abstracts e full-text (RAG)
- sugestão de tópicos e escrita das seções
- polimento final do texto
Se `--sources` for omitido, utiliza as fontes padrão: `arxiv`, `crossref`, `openalex`.

```bash
revsys run \
  --query '"lung" AND ("segmentation" OR "deep learning" OR "machine learning")' \
  --sources openalex \
  --max-records 50 \
  --output resultados.csv
```
### revsys define-directives
Define diretrizes de revisão via LLM:

```bash
revsys define-directives \
  --topic "Lung segmentation methods using deep learning" \
  --output directives.json
```

### revsys prisma-report
Gera relatório PRISMA textual:

```bash
revsys prisma-report \
  --identified 200 \
  --pretriage 150 \
  --triaged 100 \
  --fulltext 80 \
  --output prisma_report.txt
```

### revsys prisma-diagram
Gera fluxograma PRISMA visual (pré-requisito: ponto de entrada `dot` do Graphviz instalado no sistema):

```bash
revsys prisma-diagram \
  --identified 200 \
  --pretriage 150 \
  --triaged 100 \
  --fulltext 80 \
  --output prisma_flowchart.png
```


# TODO 

(ROADMAP)

## Documentação com MkDocs

> **!! Em desenvolvimento !! **
> \#BUG MKDocs implementado, mas não lista as funções!

Toda a documentação do RevSys está disponível em formato estático via [MkDocs](https://www.mkdocs.org/).

Para pré-visualizar localmente:
```bash
mkdocs serve
```
> Observação: este projeto usa o tema **Material** para MkDocs. Se você receber o erro
> "Unrecognised theme name: 'material'", instale o pacote correspondente:
```bash
pip install mkdocs-material
```

Para construir o site estático:
```bash
mkdocs build
```

## Docker

> **!! Em desenvolvimento !! **
> **\#TODO: RASCUNHO NÃO TESTADO**

Você pode rodar o sistema completo via Docker e Docker Compose:

1. Construa a imagem:
   ```bash
   docker build -t revsys .
   ```
2. Suba os serviços (Redis, CLI e Orchestrator):
   ```bash
   docker-compose up -d
   ```
3. Verifique os logs:
   ```bash
   docker-compose logs -f revsys-cli
   docker-compose logs -f revsys-orch
   ```

Para parar e remover containers:
```bash
docker-compose down
```

## Integração Contínua

> **!! Em desenvolvimento !! **
> **\#TODO: RASCUNHO NÃO TESTADO**

Este projeto utiliza **Bitbucket Pipelines** para CI. O arquivo `bitbucket-pipelines.yml` na raiz define o pipeline que:
- Instala/completa as dependências via pip
- Instala o pacote em modo editável (`pip install -e .`)
- Executa os testes com pytest

O pipeline é executado em pushes para `main` e `feature/*`, e em pull requests.
O step de instalação inclui a instalação do binário `graphviz` para suportar a geração dos diagramas PRISMA.

## Implementações Faltantes

- \#TODO: Integração com ferramentas de gerenciamento de referências (EndNote, Zotero).
- \#TODO: Suporte a LLMs locais (por exemplo, Gemma ou LLAMA).
- \#TODO: API web ou interface gráfica.
- \#TODO: Documentação de API e exemplos de notebook mais detalhados.
