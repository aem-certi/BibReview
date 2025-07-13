"""
Definição do crew RevSys via YAML config para uso com CrewAI.
"""

from typing import List
from crewai.project import CrewBase, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
import os
from crewai.task import Task

@CrewBase
class RevSysCrew:
    """Crew para revisão sistemática automatizada"""
    agents: List[BaseAgent]
    tasks: List[Task]

    # Arquivos de configuração YAML
    # Config YAML estão em '../config' relativo a este módulo
    # Config YAML estão em '../../config' relativo a este módulo
    agents_config = '../../config/agents.yaml'
    tasks_config  = '../../config/tasks.yaml'

    def crew(self):
        """Retorna a instância de crew pronta para execução"""
        return crew(self.tasks, self.agents)
    
    @task
    def search_task(self, inputs: dict) -> list[dict]:
        """
        Executa a busca usando o CSV gerado ou parâmetros de entrada.
       """
        import pandas as pd
        results_csv = inputs.get('results_csv')
        if results_csv and os.path.exists(results_csv):
            df = pd.read_csv(results_csv)
        else:
            # fallback: rerun search via subprocess
            from subprocess import run
            cmd = [
                'revsys', 'search',
                '--query', inputs.get('query', ''),
                '--max-records', str(inputs.get('max_records', 50)),
                '--output', 'tmp_search.csv'
            ]
            start = inputs.get('from_date')
            end = inputs.get('to_date')
            if start:
                cmd.extend(['--from-date', start])
            if end:
                cmd.extend(['--to-date', end])
            run(cmd, check=True)
            df = pd.read_csv('tmp_search.csv')
        # Embed the original query into each record for downstream tasks
        query_str = inputs.get('query', '')
        df['__query'] = query_str
        return df.to_dict(orient='records')

    @task
    def triage_task(self, inputs: list[dict]) -> list[dict]:
        """
        Triagem assistida por LLM: classifica cada artigo como incluído ou excluído
        com justificativa. Retorna apenas os incluídos.
        """
        # Check for OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY')
        # Fallback simple filter if no API key
        if not api_key:
            try:
                from revsys.config import MAX_RESULTS
            except ImportError:
                MAX_RESULTS = len(inputs)
            filtered = [rec for rec in inputs if rec.get('Abstract') and rec['Abstract'] != 'N/A']
            return filtered[:MAX_RESULTS]
        # Initialize OpenAI client
        from openai import OpenAI
        import json
        client = OpenAI(api_key=api_key)
        try:
            from revsys.config import GPT_MODEL, GENERATION_TEMPERATURE
        except ImportError:
            GPT_MODEL, GENERATION_TEMPERATURE = 'GPT-4.1-mini', 0.3
        included = []
        # Iterate over records and classify
        for rec in inputs:
            title = rec.get('Title', '')
            abstract = rec.get('Abstract', '')
            question = rec.get('__query', '')
            # Build prompt for classification
            prompt = (
                f"Research question: {question}\n"
                f"Title: {title}\nAbstract: {abstract}\n"
                "Should this article be INCLUDED in the systematic review based on the research question? "
                "Answer JSON with keys 'include' (true/false) and 'justification' (concise)."
            )
            try:
                resp = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=[{'role': 'user', 'content': prompt}],
                    temperature=GENERATION_TEMPERATURE
                )
                # Extract content from response
                msg = resp.choices[0].message.content
                data = json.loads(msg)
                include_flag = bool(data.get('include'))
                justification = data.get('justification', '')
            except Exception as e:
                include_flag = False
                justification = f"LLM error: {e}"
            # Append only included articles
            if include_flag:
                rec['Justification'] = justification
                included.append(rec)
        return included

    @task
    def review_task(self, inputs: list[dict]) -> dict:
        """
        Gera sumário dos artigos triados usando heurística simples ou LLM.
        Retorna dicionário com resumos por artigo.
        """
        # Se não há artigo ou chave de API, retorna stub
        count = len(inputs or [])
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {'summary': f"Processed {count} articles (no API key provided)."}
        # Importa parâmetros de LLM
        try:
            from revsys.config import GPT_MODEL, GENERATION_TEMPERATURE
        except ImportError:
            GPT_MODEL, GENERATION_TEMPERATURE = 'GPT-4.1-mini', 0.3
        # Inicializa cliente OpenAI
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        articles = []
        for rec in inputs:
            text = rec.get('Abstract', '')
            # Prompt básico para sumário
            prompt = (
                f"Please summarize the following abstract for a systematic review:\n"
                f"Title: {rec.get('Title','')}\nAbstract: {text}"
            )
            try:
                resp = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=[{'role': 'user', 'content': prompt}],
                    temperature=GENERATION_TEMPERATURE
                )
                # Extract summary from response
                summary = resp.choices[0].message.content.strip()
            except Exception as e:
                summary = f"Error generating summary: {e}"
            articles.append({'Title': rec.get('Title'), 'Summary': summary})
        return {'articles': articles}