import os
import pytest

from revsys.pretriage import pretriage_records


class DummyEmbed:
    def __init__(self, embedding):
        self.embedding = embedding

def test_pretriage_filters_records(monkeypatch):
    # Configura chave de API fake
    monkeypatch.setenv('OPENAI_API_KEY', 'test_key')
    # Prepara registros de teste
    records = [
        {'Title': 'A', 'Abstract': ''},
        {'Title': 'B', 'Abstract': 'Some abstract'}
    ]
    inclusion_keys = ['include_term']
    exclusion_keys = ['exclude_term']

    # Monkeypatch de openai.Embedding.create para retornar embeddings controlados
    def fake_embedding_create(model, input):
        data = []
        # Embedding para termos de inclusão
        if input == inclusion_keys:
            for _ in input:
                data.append(DummyEmbed([1.0, 0.0]))
        # Embedding para termos de exclusão
        elif input == exclusion_keys:
            for _ in input:
                data.append(DummyEmbed([0.0, 1.0]))
        # Embedding para registros
        else:
            for idx, _ in enumerate(input):
                # Primeiro registro semelhante ao termo de inclusão
                if idx == 0:
                    data.append(DummyEmbed([1.0, 0.0]))
                # Segundo registro semelhante ao termo de exclusão
                else:
                    data.append(DummyEmbed([0.0, 1.0]))
        return {'data': data}

    import openai
    monkeypatch.setattr(openai.Embedding, 'create', fake_embedding_create)

    # Executa pré-triagem com thresholds que passam apenas o primeiro registro
    filtered = pretriage_records(
        records,
        inclusion_keys,
        exclusion_keys,
        incl_threshold=0.5,
        excl_threshold=0.5
    )
    # Deve manter apenas o registro 'A'
    titles = [rec['Title'] for rec in filtered]
    assert titles == ['A']

def test_pretriage_no_api_key():
    # Remove chave de API
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    # Deve lançar RuntimeError sem chave
    with pytest.raises(RuntimeError):
        pretriage_records([], ['term'])