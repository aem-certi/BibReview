import pytest

from revsys.clients.crossref import CrossrefAPI


@pytest.fixture
def sample_crossref_data():
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1000/testdoi",
                    "title": ["Test Title"],
                    "container-title": ["Journal X"],
                    "issued": {"date-parts": [[2023, 5, 20]]},
                    "author": [{"given": "John", "family": "Doe"}],
                    "abstract": "<p>Sample <b>abstract</b> text.</p>",
                    "language": "en",
                    "type": "journal-article",
                    "license": [{"URL": "http://license"}],
                    "URL": "http://example.com/download.pdf",
                    "is-referenced-by-count": 10
                }
            ]
        }
    }

def test_crossref_process_data_cleaning(sample_crossref_data):
    api = CrossrefAPI(rows=5)
    records = api.process_data(sample_crossref_data)
    assert isinstance(records, list) and len(records) == 1
    rec = records[0]
    # Verifica limpeza de HTML no abstract
    assert rec.get('Abstract') == 'Sample abstract text.'
    # Verifica preenchimento de colunas padronizadas
    assert rec.get('DOI') == '10.1000/testdoi'
    assert rec.get('Title') == 'Test Title'
    assert rec.get('Journal') == 'Journal X'
    # Verifica formato de Authors Year
    assert 'Doe' in rec.get('Authors Year')