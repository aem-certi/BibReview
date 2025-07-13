import click
import pandas as pd
import subprocess

from revsys.clients.arxiv import ArxivFetcher
from revsys.clients.crossref import CrossrefAPI
from revsys.clients.openalex import PyAlexFetcher
from revsys.clients.plos import PlosAPI
from revsys.clients.pubmed_api import PubMedAPI
from revsys.clients.scopus import ScopusFetcher
from revsys.clients.springernature import SpringerNature
from revsys.clients.scholar import ScholarClient
from revsys.clients.ieee import IeeeXplore
from revsys.config import OPENALEX_EMAIL, SPRINGER_API_KEY, SCOPUS_API_KEY, PUBMED_API_KEY, IEEE_API_KEY
from revsys.pretriage import pretriage_records
import os
import requests
import pandas as pd
import pdb



@click.group()
def cli():
    """Revsys CLI for systematic review"""
    pass



@cli.command()
@click.option('--query', '-q', required=True, multiple=True, help='Search query')
@click.option('--sources', '-s', multiple=True,
               type=click.Choice(['arxiv','crossref','openalex','plos','pubmed','scopus','springernature','scholar','ieee']),
               help='Sources to search (default: all)')
@click.option('--from-date', help='Start date (YYYY-MM-DD) for sources that support it')
@click.option('--to-date', help='End date (YYYY-MM-DD) for sources that support it')
@click.option('--max-records', '-m', default=100, show_default=True, help='Max records per source')
@click.option('--output', '-o', default='results.csv', help='CSV output path')


def search(query, sources, from_date, to_date, max_records, output):
    """Search multiple sources and save to CSV"""
    # Mantém apenas fontes abertas sem necessidade de chave ou cadastro
    default_sources = ['arxiv', 'crossref', 'openalex']
    sources_list = list(sources) if sources else default_sources    
    query_list = list(query)
    df_list = []
    for qry in query_list:
        for src in sources_list:
            click.echo(f"Searching {src}...")
            try:
                if src == 'arxiv':
                    start_year = int(from_date.split('-')[0]) if from_date else None
                    end_year = int(to_date.split('-')[0]) if to_date else None
                    df = ArxivFetcher().fetch_references(
                        query=qry,
                        max_results=max_records,
                        start_year=start_year,
                        end_year=end_year,
                        total_limit=max_records
                    )
                elif src == 'crossref':
                    df = CrossrefAPI(rows=max_records).run_pipeline(
                        query=qry,
                        max_records=max_records,
                        from_date=from_date,
                        to_date=to_date
                    )
                    if df.empty:
                        raise ValueError("Crossref returned an empty dataframe - no data collected.") #added error handling
                elif src == 'openalex':
                    df = PyAlexFetcher(email=OPENALEX_EMAIL).fetch_references(query=query, n_max=max_records)
                elif src == 'plos':
                    df = PlosAPI(rows=max_records).run_pipeline(query=query, max_records=max_records)
                elif src == 'pubmed':
                    df = PubMedAPI(api_key=PUBMED_API_KEY).search(
                        query=qry,
                        retmax=max_records,
                        from_date=from_date,
                        to_date=to_date
                    )
                elif src == 'scopus':
                    if from_date and to_date:
                        dr = f"{from_date.split('-')[0]}-{to_date.split('-')[0]}"
                        df = ScopusFetcher(api_key=SCOPUS_API_KEY).fetch_references(
                            query=qry,
                            count=max_records,
                            date_research=dr
                        )
                    else:
                        df = ScopusFetcher(api_key=SCOPUS_API_KEY).fetch_references(
                            query=qry,
                            count=max_records
                        )
                elif src == 'springernature':
                    df = SpringerNature(api_key=SPRINGER_API_KEY).run_pipeline(
                        q=qry,
                        p=max_records,
                        from_date=from_date,
                        to_date=to_date,
                        max_records=max_records
                    )
                elif src == 'scholar':
                    # client = ScholarClient(use_proxy=True)
                    # client.refresh_proxy()
                    df = ScholarClient(use_proxy=True).search(query=qry, max_records=max_records)
                elif src == 'ieee':
                    sy = int(from_date.split('-')[0]) if from_date else None
                    ey = int(to_date.split('-')[0]) if to_date else None
                    df = IeeeXplore(api_key=IEEE_API_KEY).fetch_references(
                        query=qry,
                        max_records=max_records,
                        start_year=sy,
                        end_year=ey
                    )
                else:
                    click.echo(f"Unknown source: {src}", err=True)
                    continue
            except Exception as e:
                click.echo(f"Error searching {src}: {e}", err=True)
                continue
            if not df.empty:
                df_list.append(df)
        if df_list:
            # Concatena resultados e remove duplicatas por DOI e Título
            result = pd.concat(df_list, ignore_index=True)
            result.drop_duplicates(subset=['DOI', 'Title'], keep='first', inplace=True)
            result.to_csv(output, index=False)
            click.echo(f"Saved {len(result)} records to {output}")
        else:
            click.echo("No records found.", err=True)

@cli.command()
@click.option('--query', '-q', required=True, help='Search query for full pipeline')
@click.option('--sources', '-s', multiple=True,
               type=click.Choice(['arxiv','crossref','openalex','plos','pubmed','scopus','springernature','scholar','ieee']),
               help='Sources to search (default: all)')
@click.option('--from-date', help='Start date (YYYY-MM-DD) for sources that support it')
@click.option('--to-date', help='End date (YYYY-MM-DD) for sources that support it')
@click.option('--max-records', '-m', default=50, show_default=True, help='Max records per source')
@click.option('--output', '-o', default='results.csv', help='CSV output path for search step')
def run(query, sources, from_date, to_date, max_records, output):
    """Run full pipeline: search, triage and review via orchestrator"""
    # Chamando o orquestrador multiagente
    cmd = ['python', '-m', 'revsys.orchestrator', '--query', query]
    for src in sources:
        cmd.extend(['--sources', src])
    if from_date:
        cmd.extend(['--from-date', from_date])
    if to_date:
        cmd.extend(['--to-date', to_date])
    cmd.extend(['--max-records', str(max_records), '--output', output])
    subprocess.run(cmd, check=True)

@cli.command()
@click.option('--query', '-q', required=True, help='Research question to guide triage')
@click.option('--incl-key', '-ik', 'incl_keys', multiple=True,
               help='Term(s) for inclusion pre‑triage via embeddings')
@click.option('--excl-key', '-ek', 'excl_keys', multiple=True,
               help='Term(s) for exclusion pre‑triage via embeddings')
@click.option('--incl-threshold', type=float, default=0.3, show_default=True,
               help='Similarity threshold for inclusion pre‑triage')
@click.option('--excl-threshold', type=float, default=0.3, show_default=True,
               help='Similarity threshold for exclusion pre‑triage')
@click.option('--input', '-i', 'input_csv', required=True, help='CSV input file for triage')
@click.option('--output', '-o', 'output_csv', default='triaged.csv', help='CSV output path for triaged results')
@click.option('--workers', '-w', type=int, default=1, show_default=True,
               help='Number of parallel workers for LLM classification')
def triage(query, incl_keys, excl_keys, incl_threshold, excl_threshold, input_csv, output_csv, workers):
    """Run AI-assisted triage on search results CSV"""
    # Carrega registros e aplica pré-triagem por embeddings, se solicitado
    df = pd.read_csv(input_csv)
    records = df.to_dict(orient='records')
    if incl_keys:
        try:
            records = pretriage_records(
                records,
                list(incl_keys),
                list(excl_keys),
                float(incl_threshold),
                float(excl_threshold)
            )
            click.echo(f"✅ [Pre-triage] {len(records)} registros após filtro semântico.")
        except Exception as e:
            click.echo(f"⚠️ [Pre-triage] Falha no filtro semântico: {e}", err=True)
    
    # Checa API key para triagem assistida por LLM
    api_key = os.getenv('OPENAI_API_KEY')
    # Fallback to simple filter if no API key
    if not api_key:
        # Simple filter: only retain records with non-empty string abstracts
        filtered = [
            rec for rec in records
            if isinstance(rec.get('Abstract'), str)
               and rec['Abstract'].strip()
               and rec['Abstract'].strip().upper() != 'N/A'
        ]
        df_tri = pd.DataFrame(filtered)
        df_tri.to_csv(output_csv, index=False)
        click.echo(f"Saved {len(df_tri)} triaged records to {output_csv} (simple filter)")
        return
    # Initialize OpenAI client
    from openai import OpenAI
    import json
    from revsys.config import GPT_MODEL, GENERATION_TEMPERATURE
    client = OpenAI(api_key=api_key)
    # Função que classifica um registro e retorna-o se incluído
    def classify_record(rec):
        prompt = (
            f"Research question: {query}\n"
            f"Title: {rec.get('Title','')}\nAbstract: {rec.get('Abstract','')}\n"
            "Should this article be INCLUDED in the systematic review based on the research question? "
            "Answer JSON with keys 'include' (true/false) and 'justification' (concise)."
        )
        try:
            resp = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=GENERATION_TEMPERATURE
            )
            msg = resp.choices[0].message.content
            cleaned_msg = msg.strip().replace('```json\n', '').replace('\n```', '') #added to remove the markdown fences and any leading/trailing whitespace
            data = json.loads(cleaned_msg)
            if data.get('include'):
                rec['Justification'] = data.get('justification', '')
                return rec
        except Exception as e:
            click.echo(f"Error classifying record '{rec.get('Title','')[:50]}...': {e}", err=True)
        return None

    included = []
    # Classificação paralela ou sequencial
    if workers and workers > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for result in executor.map(classify_record, records):
                if result:
                    included.append(result)
    else:
        for rec in records:
            result = classify_record(rec)
            if result:
                included.append(result)
    # Salva registros incluídos
    df_tri = pd.DataFrame(included)
    df_tri.to_csv(output_csv, index=False)
    click.echo(f"Saved {len(df_tri)} triaged records to {output_csv}")

@cli.command()
@click.option('--input', '-i', 'input_csv', required=True, help='CSV input file for review')
@click.option('--output', '-o', 'output', default=None, help='Output path for review results (CSV or TXT)')
def review(input_csv, output):
    """Run AI-assisted review on triaged articles"""
    # Load records from CSV
    df = pd.read_csv(input_csv)
    records = df.to_dict(orient='records')
    # Check API key for LLM-assisted review
    api_key = os.getenv('OPENAI_API_KEY')
    count = len(records)
    if not api_key:
        # Fallback summary
        summary = f"Processed {count} articles (no API key provided)."
        out = output or input_csv.replace('.csv', '_summary.txt')
        with open(out, 'w') as f:
            f.write(summary)
        click.echo(f"Saved review summary to {out} (fallback)")
        return
    # LLM-assisted review: summarize each abstract
    from openai import OpenAI
    from revsys.config import GPT_MODEL, GENERATION_TEMPERATURE
    # Instancia cliente OpenAI
    client = OpenAI(api_key=api_key)
    articles = []
    for rec in records:
        title = rec.get('Title', '')
        abstract = rec.get('Abstract', '')
        prompt = (
            f"Please summarize the following abstract for a systematic review:\n"
            f"Title: {title}\nAbstract: {abstract}"
        )
        try:
            resp = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=GENERATION_TEMPERATURE
            )
            summary = resp.choices[0].message.content.strip()
        except Exception as e:
            summary = f"Error generating summary: {e}"
        articles.append({'Title': title, 'Summary': summary})
    # Save detailed summaries
    df_rev = pd.DataFrame(articles)
    out = output or input_csv.replace('.csv', '_review.csv')
    df_rev.to_csv(out, index=False)
    click.echo(f"Saved detailed review to {out} (LLM)")

@cli.command(name='download-pdfs')
@click.option('--input', '-i', 'input_csv', required=True, help='CSV input with Download URL column')
@click.option('--failure-output', '-f', 'failure_csv', default=None, help='CSV input with failed Download URL column')
@click.option('--output-dir', '-d', 'output_dir', default=None, help='Directory to save downloaded PDFs')
def download_pdfs(input_csv, failure_csv, output_dir):
    """Download PDFs for articles listed in CSV"""
    df = pd.read_csv(input_csv)
    out_dir = output_dir or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    failed_list=[]
    for rec in df.to_dict(orient='records'):
        # Get and sanitize download URL
        url = rec.get('Download URL') or rec.get('DownloadURL')
        url_str = str(url).strip()
        # Skip if URL is not a valid HTTP/HTTPS link
        if not url_str.lower().startswith(('http://', 'https://')):
            failed_list.append(rec)
            click.echo(f"Skipping record {rec.get('ID','')} - invalid or missing Download URL.")
            continue
        # Determine identifier for filename (DOI or ID)
        _id = rec.get('DOI') or rec.get('ID') or ''
        _id_str = str(_id)
        if _id_str == 'nan':
            _id_str = url_str
        # Sanitize filename: keep alphanumeric, underscore, hyphen
        fname = ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in _id_str) + '.pdf'
        dest = os.path.join(out_dir, fname)
        try:
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            with open(dest, 'wb') as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            click.echo(f"Downloaded PDF for {rec.get('Title', rec.get('ID'))} -> {dest}")
            count += 1
        except Exception as e:
            click.echo(f"Failed to download {url}: {e}", err=True)
            failed_list.append(rec)
    df = pd.DataFrame(failed_list)
    df.to_csv(failure_csv, index=False)
    click.echo(f"Downloaded {count} PDFs to {out_dir}")

@cli.command(name='fetch-fulltext')
@click.option('--input', '-i', 'input_csv', required=True, help='CSV input with DOI or Download URL')
@click.option('--output-dir', '-d', 'output_dir', default='fulltexts', help='Directory to save PDFs and text')
@click.option('--output', '-o', 'output_json', default=None, help='Output JSON file with full-text content')
@click.option('--no-unpaywall', 'use_unpaywall', flag_value=False, default=True,
               help='Desabilitar uso da API Unpaywall para localizar PDFs')
def fetch_fulltext_cmd(input_csv, output_dir, output_json, use_unpaywall):
    """Download PDFs e extrai texto completo de artigos listados em CSV"""
    import json
    from revsys.fulltext import fetch_fulltext
    df = pd.read_csv(input_csv)
    records = df.to_dict(orient='records')
    click.echo(f"📰 Processando {len(records)} registros para full-text...")
    results = fetch_fulltext(records, output_dir=output_dir, use_unpaywall=use_unpaywall)
    # Define arquivo de saída
    out = output_json or input_csv.replace('.csv', '_fulltext.json')
    try:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        click.echo(f"💾 Salvou full-text em {out}")
    except Exception as e:
        click.echo(f"⚠️ Falha ao salvar full-text: {e}", err=True)
    
@cli.command(name='define-directives')
@click.option('--topic', '-t', required=True, help='Brief description of the review topic')
@click.option('--output', '-o', 'output_json', default='directives.json', help='Output JSON file with directives')
def define_directives_cmd(topic, output_json):
    """Define research question, criteria and query via LLM"""
    import json
    from revsys.directives import define_directives
    click.echo(f"✍️ Definindo diretrizes para: {topic}")
    directives = define_directives(topic)
    try:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(directives, f, ensure_ascii=False, indent=2)
        click.echo(f"💾 Salvo directives em {output_json}")
    except Exception as e:
        click.echo(f"⚠️ Falha ao salvar directives: {e}", err=True)

@cli.command(name='review-fulltext')
@click.option('--query', '-q', required=True, help='Research question to guide full-text review')
@click.option('--input', '-i', 'input_json', required=True, help='JSON input from fetch-fulltext')
@click.option('--output', '-o', 'output_json', default=None, help='Output JSON with full-text summaries')
@click.option('--chunk-size', type=int, default=2000, show_default=True, help='Chunk size in characters')
@click.option('--overlap', type=int, default=200, show_default=True, help='Overlap size in characters')
@click.option('--top-k', type=int, default=5, show_default=True, help='Number of chunks to retrieve')
def review_fulltext_cmd(query, input_json, output_json, chunk_size, overlap, top_k):
    """Run RAG-based review on full-text and generate summaries"""
    import json
    import os
    import openai
    from revsys.rag import chunk_text, build_vector_store, retrieve
    from revsys.config import GPT_MODEL, GENERATION_TEMPERATURE
    api_key = os.getenv('OPENAI_API_KEY')
    # Fallback se não há chave: exporta full_text bruto
    try:
        with open(input_json, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except Exception as e:
        click.echo(f"⚠️ Falha ao ler {input_json}: {e}", err=True)
        return
    if not api_key:
        click.echo('⚠️ OPENAI_API_KEY não definido para review-fulltext; usando fallback de full_text', err=True)
        summaries = []
        for rec in records:
            summaries.append({'Title': rec.get('Title', ''), 'Summary': rec.get('full_text', '')})
        out = output_json or input_json.replace('.json', '_fullreview.json')
        try:
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, ensure_ascii=False, indent=2)
            click.echo(f"💾 Salvou fallback de full-text review em {out}")
        except Exception as e:
            click.echo(f"⚠️ Falha ao salvar full-text review fallback: {e}", err=True)
        return
    # Instancia cliente OpenAI
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    records = []
    try:
        with open(input_json, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except Exception as e:
        click.echo(f"⚠️ Falha ao ler {input_json}: {e}", err=True)
        return
    summaries = []
    for rec in records:
        title = rec.get('Title', '')
        text = rec.get('full_text', '')
        if not text:
            summ = ''
        else:
            chunks = chunk_text(text, chunk_size, overlap)
            store = build_vector_store(chunks)
            relevant = retrieve(query, store, top_k)
            prompt = f"Please summarize the following excerpts in relation to the research question: {query}\n\n"
            for idx, ex in enumerate(relevant):
                prompt += f"Excerpt {idx+1}: {ex}\n\n"
            resp = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{'role':'user','content':prompt}],
                temperature=GENERATION_TEMPERATURE
            )
            summ = resp.choices[0].message.content.strip()
        summaries.append({'Title': title, 'Summary': summ})
    out = output_json or input_json.replace('.json', '_fullreview.json')
    try:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, ensure_ascii=False, indent=2)
        click.echo(f"💾 Salvou full-text review em {out}")
    except Exception as e:
        click.echo(f"⚠️ Falha ao salvar full-text review: {e}", err=True)

@cli.command(name='suggest-topics')
@click.option('--input', '-i', 'input_json', required=True, help='JSON input with document summaries')
@click.option('--question', '-q', required=True, help='Research question for topic suggestion')
@click.option('--output', '-o', 'output_json', default=None, help='Output JSON with suggested topics')
@click.option('--top-n', type=int, default=5, show_default=True, help='Max number of topics to suggest')
def suggest_topics_cmd(input_json, question, output_json, top_n):
    """Suggest review topics based on document summaries"""
    import json
    from revsys.topics import suggest_topics
    try:
        docs = json.load(open(input_json, 'r', encoding='utf-8'))
    except Exception as e:
        click.echo(f"⚠️ Falha ao ler {input_json}: {e}", err=True)
        return
    topics = suggest_topics(question, docs, top_n)
    out = output_json or input_json.replace('.json', '_topics.json')
    try:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(topics, f, ensure_ascii=False, indent=2)
        click.echo(f"💾 Salvou tópicos sugeridos em {out}")
    except Exception as e:
        click.echo(f"⚠️ Falha ao salvar tópicos: {e}", err=True)

@cli.command(name='write-topics')
@click.option('--topics', '-t', 'topics_json', required=True, help='JSON file with topics list')
@click.option('--docs', '-d', 'docs_json', required=True, help='JSON file with document summaries')
@click.option('--question', '-q', required=True, help='Research question')
@click.option('--inclusion', multiple=True, help='Inclusion criteria items')
@click.option('--exclusion', multiple=True, help='Exclusion criteria items')
@click.option('--output', '-o', 'output_json', default=None, help='Output JSON with topic texts')
def write_topics_cmd(topics_json, docs_json, question, inclusion, exclusion, output_json):
    """Write sections for each suggested topic"""
    import json
    from revsys.topics import write_topic
    try:
        topics = json.load(open(topics_json, 'r', encoding='utf-8'))
        docs = json.load(open(docs_json, 'r', encoding='utf-8'))
    except Exception as e:
        click.echo(f"⚠️ Falha ao ler arquivos: {e}", err=True)
        return
    output = {}
    for topic in topics:
        click.echo(f"✍️ Escrevendo seção: {topic}")
        text = write_topic(topic, question, docs, list(inclusion), list(exclusion))
        output[topic] = text
    out = output_json or topics_json.replace('.json', '_sections.json')
    try:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        click.echo(f"💾 Salvou seções de tópicos em {out}")
    except Exception as e:
        click.echo(f"⚠️ Falha ao salvar seções: {e}", err=True)

@cli.command(name='polish')
@click.option('--question', '-q', required=True, help='Research question')
@click.option('--inclusion', multiple=True, help='Inclusion criteria items')
@click.option('--exclusion', multiple=True, help='Exclusion criteria items')
@click.option('--input', '-i', 'sections_json', required=True, help='JSON file with topic sections')
@click.option('--output', '-o', 'output_file', default=None, help='Output file for polished review')
def polish_cmd(question, inclusion, exclusion, sections_json, output_file):
    """Polish the entire review, consolidating all sections"""
    import json
    from revsys.topics import polish_review
    try:
        sections = json.load(open(sections_json, 'r', encoding='utf-8'))
    except Exception as e:
        click.echo(f"⚠️ Falha ao ler seções: {e}", err=True)
        return
    final = polish_review(question, list(inclusion), list(exclusion), sections)
    out = output_file or sections_json.replace('.json', '_final.txt')
    try:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(final)
        click.echo(f"💾 Salvou revisão final em {out}")
    except Exception as e:
        click.echo(f"⚠️ Falha ao salvar revisão final: {e}", err=True)

@cli.command(name='prisma-report')
@click.option('--identified', type=int, required=True, help='Number of records identified')
@click.option('--pretriage', type=int, help='Number after pre-triage')
@click.option('--triaged', type=int, help='Number after triage')
@click.option('--fulltext', type=int, help='Number of full-text retrieved')
@click.option('--output', '-o', 'output_file', default=None, help='Output file for PRISMA report')
def prisma_report_cmd(identified, pretriage, triaged, fulltext, output_file):
    """Generate a simple PRISMA report"""
    from revsys.prisma import generate_prisma_report
    counts = {
        'identified': identified,
        'pretriage': pretriage,
        'triaged': triaged,
        'fulltext': fulltext
    }
    report = generate_prisma_report(counts)
    out = output_file or 'prisma_report.txt'
    try:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(report)
        click.echo(f"💾 Salvou PRISMA report em {out}")
    except Exception as e:
        click.echo(f"⚠️ Falha ao salvar PRISMA report: {e}", err=True)

@cli.command(name='prisma-diagram')
@click.option('--identified', type=int, required=True, help='Number of records identified')
@click.option('--pretriage', type=int, help='Number after pre-triage')
@click.option('--triaged', type=int, help='Number after triage')
@click.option('--fulltext', type=int, help='Number of full-text retrieved')
@click.option('--output', '-o', 'output_file', default=None, help='Output file for PRISMA diagram (e.g., .png, .svg)')
def prisma_diagram_cmd(identified, pretriage, triaged, fulltext, output_file):
    """Generate a PRISMA flowchart diagram"""
    import shutil
    # Verifica se o binário 'dot' do Graphviz está disponível
    if shutil.which('dot') is None:
        click.echo("⚠️ Executável 'dot' do Graphviz não encontrado. Instale o Graphviz para gerar o diagrama PRISMA.")
        return
    from revsys.prisma import generate_prisma_diagram
    counts = {
        'identified': identified,
        'pretriage': pretriage,
        'triaged': triaged,
        'fulltext': fulltext
    }
    out = output_file or 'prisma_flowchart.png'
    try:
        path = generate_prisma_diagram(counts, out)
        click.echo(f"💾 PRISMA diagram saved to {path}")
    except Exception as e:
        click.echo(f"⚠️ Falha ao gerar diagrama PRISMA: {e}", err=True)


if __name__ == '__main__':
    cli()