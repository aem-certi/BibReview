import os
import csv
import pytest

from click.testing import CliRunner
from revsys.cli import cli


def test_cli_triage_fallback(tmp_path, monkeypatch):
    # Prepara CSV de entrada
    input_csv = tmp_path / 'input.csv'
    rows = [{'Title': 'Test', 'Abstract': 'Some abstract text.'}]
    with open(input_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Title', 'Abstract'])
        writer.writeheader()
        writer.writerows(rows)
    output_csv = tmp_path / 'triaged.csv'

    # Garante que não há chave de API
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['triage', '--query', 'topic', '--input', str(input_csv), '--output', str(output_csv)]
    )
    # CLI deve executar sem erro
    assert result.exit_code == 0, result.output
    # Arquivo de saída deve existir e conter o registro
    assert output_csv.exists()
    with open(output_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        lines = list(reader)
    assert len(lines) == 1
    assert lines[0]['Title'] == 'Test'