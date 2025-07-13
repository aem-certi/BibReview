import pytest
from click.testing import CliRunner
import revsys.cli as cli_mod

def test_run_invokes_orchestrator(monkeypatch):
    # Captura chamadas ao subprocess.run
    calls = []
    def fake_run(cmd, check):
        calls.append((cmd, check))
    monkeypatch.setattr(cli_mod.subprocess, 'run', fake_run)
    # Executa o comando CLI
    runner = CliRunner()
    result = runner.invoke(
        cli_mod.cli,
        ['run', '--query', 'topic', '--max-records', '10', '--output', 'out.csv']
    )
    # Deve terminar sem erros
    assert result.exit_code == 0, result.output
    # Verifica chamada ao orchestrator
    assert len(calls) == 1
    cmd, check = calls[0]
    assert check is True
    # Verifica estrutura do comando
    assert cmd[:3] == ['python', '-m', 'revsys.orchestrator']
    assert '--query' in cmd and 'topic' in cmd
    assert '--max-records' in cmd and '10' in cmd
    assert '--output' in cmd and 'out.csv' in cmd