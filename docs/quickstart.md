 # Quickstart

 Este guia rápido mostra como configurar e usar o RevSys para uma revisão sobre *deep learning para segmentação de doença intersticial pulmonar*.

 ## 1. Instalação

 ```bash
 # Clonar o repositório
 git clone <URL-do-repo>
 cd <repo>

 # Criar e ativar ambiente virtual (opcional)
 python -m venv .venv
 source .venv/bin/activate  # Linux/macOS
 .\.venv\\Scripts\\activate  # Windows

 # Instalar dependências
 pip install -r requirements.txt
 pip install -e .
 ```

 ## 2. Variáveis de Ambiente
 Crie um arquivo `.env` na raiz do projeto com:

 ```
 OPENAI_API_KEY=<sua_chave_openai>
 OPENALEX_EMAIL=<seu_email>
 SPRINGER_API_KEY=<sua_chave_springer>  # opcional
 SCOPUS_API_KEY=<sua_chave_scopus>      # opcional
 PUBMED_API_KEY=<sua_chave_pubmed>      # opcional
 IEEE_API_KEY=<sua_chave_ieee>          # opcional
 CACHE_ENABLED=true                    # opcional
 CACHE_EXPIRE=3600                     # opcional (segundos)
 ```

 ## 3. Exemplo de Execução

 ### Busca
 ```bash
 revsys search \
   --query "interstitial lung disease segmentation deep learning" \
   --output results.csv
 ```

 ### Triagem
 ```bash
 revsys triage \
   --query "Métodos de DL para segmentação de doença intersticial pulmonar" \
   --incl-key segmentation \
   --incl-key lung \
   --incl-key deep learning \
   --input results.csv \
   --output triaged.csv \
   --workers 4
 ```

 ### Download de PDFs
 ```bash
 revsys download-pdfs \
   --input triaged.csv \
   --output-dir pdfs/
 ```

 ### Extração de Full-text
 ```bash
 revsys fetch-fulltext \
   --input triaged.csv \
   --output-dir fulltexts/ \
   --output triaged_fulltext.json
 ```

 ### Diagrama PRISMA
 ```bash
 revsys prisma-diagram \
   --identified 200 \
   --pretriage 150 \
   --triaged 100 \
   --fulltext 80 \
   --output prisma_flowchart.png
 ```