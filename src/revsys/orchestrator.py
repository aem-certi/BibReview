"""
Orquestra o pipeline completo de revisão sistemática:
busca, definição de diretrizes, triagem, revisão,
sugestão de tópicos, escrita de seções e polimento final.
"""

import os
import subprocess
import pandas as pd
import click

import sys

@click.command()
@click.option('--query', '-q', required=True,
              help='Termo de busca (e tema para as diretrizes)')
@click.option(
    '--sources', '-s', multiple=True,
    default=['arxiv', 'crossref', 'openalex'],
    help='Fontes a consultar (default: arxiv, crossref, openalex)'
)
@click.option('--from-date', help='Data inicial (YYYY-MM-DD)')
@click.option('--to-date', help='Data final (YYYY-MM-DD)')
@click.option('--max-records', '-m', default=50, show_default=True, help='Máximo de registros por fonte')
@click.option('--output', '-o', default='results.csv', help='CSV de saída')
def main(query, sources, from_date, to_date, max_records, output):
    """Orquestra o pipeline completo de revisão (search → directives → triage → review → topics → write → polish)"""
    # 1. Definir diretrizes (pergunta, critérios e query)
    click.echo("✍️ [Directives] Definindo diretrizes via LLM...")
    directives_file = 'directives.json'
    subprocess.run([
        'revsys', 'define-directives',
        '--topic', query,
        '--output', directives_file
    ], check=True)
    import json
    with open(directives_file, 'r', encoding='utf-8') as f:
        directives = json.load(f)
    # Usa a query refinada se disponível
    search_query = directives.get('search_query', query)
    click.echo(f"✅ [Directives] Salvas em {directives_file}")

    # 2. SearchAgent via CLI
    click.echo("🔍 [SearchAgent] Iniciando busca...")
    cmd = [
        'revsys', 'search',
        '--query', search_query,
        '--max-records', str(max_records),
        '--output', output
    ]
    for src in sources:
        cmd.extend(['--sources', src])
    if from_date:
        cmd.extend(['--from-date', from_date])
    if to_date:
        cmd.extend(['--to-date', to_date])
    subprocess.run(cmd, check=True)
    df = pd.read_csv(output)
    click.echo(f"✅ [SearchAgent] Retornou {len(df)} artigos usando query refinada")

    # 3. Triage com base nos critérios
    triaged_csv = output.replace('.csv', '_triaged.csv')
    click.echo("🤖 [TriageAgent] Executando triagem assistida por IA...")
    cmd_triage = [
        'revsys', 'triage',
        '--query', directives.get('research_question', query),
    ]
    for ic in directives.get('inclusion_keys', []):
        cmd_triage += ['--incl-key', ic]
    for ec in directives.get('exclusion_keys', []):
        cmd_triage += ['--excl-key', ec]
    cmd_triage += ['--input', output, '--output', triaged_csv]
    subprocess.run(cmd_triage, check=True)
    df_tri = pd.read_csv(triaged_csv)
    click.echo(f"✅ [TriageAgent] {len(df_tri)} registros após triagem (arquivo: {triaged_csv})")

    # 4. Review de abstracts
    review_csv = output.replace('.csv', '_review.csv')
    click.echo("🤖 [ReviewAgent] Resumindo artigos triados (abstract)...")
    subprocess.run([
        'revsys', 'review',
        '--input', triaged_csv,
        '--output', review_csv
    ], check=True)
    click.echo(f"✅ [ReviewAgent] Resumos de abstracts salvos em {review_csv}")

    # 4b. Download & extração de full-text
    fulltext_json = output.replace('.csv', '_fulltext.json')
    click.echo("📰 [FullText] Baixando e extraindo full-text de artigos...")
    subprocess.run([
        'revsys', 'fetch-fulltext',
        '--input', triaged_csv,
        '--output-dir', 'fulltexts',
        '--output', fulltext_json
    ], check=True)
    click.echo(f"✅ [FullText] Conteúdo completo salvo em {fulltext_json}")

    # 4c. RAG review do full-text
    fullreview_json = output.replace('.csv', '_fullreview.json')
    click.echo("🤖 [FullTextReview] Sumariando texto completo via RAG...")
    subprocess.run([
        'revsys', 'review-fulltext',
        '--query', directives.get('research_question', query),
        '--input', fulltext_json,
        '--output', fullreview_json
    ], check=True)
    click.echo(f"✅ [FullTextReview] Resumos full-text salvos em {fullreview_json}")

    # 5. Sugestão de tópicos (baseada em full-text)
    topics_json = output.replace('.csv', '_topics.json')
    click.echo("🤖 [TopicsAgent] Sugerindo tópicos de revisão (full-text)...")
    subprocess.run([
        'revsys', 'suggest-topics',
        '--input', fullreview_json,
        '--question', directives.get('research_question', query),
        '--output', topics_json
    ], check=True)
    click.echo(f"✅ [TopicsAgent] Tópicos salvos em {topics_json}")

    # 6. Escrita de seções para cada tópico (full-text)
    sections_json = output.replace('.csv', '_sections.json')
    click.echo("🤖 [WriteTopics] Gerando seções para cada tópico...")
    cmd_write = [
        'revsys', 'write-topics',
        '--topics', topics_json,
        '--docs', fullreview_json,
        '--question', directives.get('research_question', query),
    ]
    for ic in directives.get('inclusion_criteria', []):
        cmd_write += ['--inclusion', ic]
    for ec in directives.get('exclusion_criteria', []):
        cmd_write += ['--exclusion', ec]
    cmd_write += ['--output', sections_json]
    subprocess.run(cmd_write, check=True)
    click.echo(f"✅ [WriteTopics] Seções salvas em {sections_json}")

    # 7. Polimento final
    final_txt = output.replace('.csv', '_final.txt')
    click.echo("🤖 [Polish] Polindo revisão final...")
    cmd_polish = [
        'revsys', 'polish',
        '--question', directives.get('research_question', query),
    ]
    for ic in directives.get('inclusion_criteria', []):
        cmd_polish += ['--inclusion', ic]
    for ec in directives.get('exclusion_criteria', []):
        cmd_polish += ['--exclusion', ec]
    cmd_polish += ['--input', sections_json, '--output', final_txt]
    subprocess.run(cmd_polish, check=True)
    click.echo(f"✅ [Polish] Revisão final salva em {final_txt}")

    click.echo(f"🎉 Processo finalizado. Revisão completa: {final_txt}")

if __name__ == '__main__':
    main()