import os
import json
import pytest

from revsys.fulltext import fetch_fulltext

class FakeResponse:
    def __init__(self, content=b'', status_code=200):
        self.content = content
        self.status_code = status_code
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f'Status code: {self.status_code}')
    def iter_content(self, chunk_size=1024):
        yield self.content

@pytest.fixture(autouse=True)
def no_unpaywall_env(monkeypatch):
    # Desabilita uso de Unpaywall por default
    monkeypatch.setenv('OPENALEX_EMAIL', '')
    yield

def test_fetch_fulltext_html(tmp_path, monkeypatch):
    # Prepara um registro com URL de HTML
    records = [{'Download URL': 'http://example.com/test.html', 'DOI': '10.1234/test'}]
    html_content = b"<html><body><p>Hello <b>world</b>!</p></body></html>"
    # Monkeypatch de requests.get para retornar HTML
    import revsys.fulltext as ftmod
    monkeypatch.setattr(ftmod.requests, 'get', lambda url, **kw: FakeResponse(content=html_content))

    results = fetch_fulltext(records, str(tmp_path), use_unpaywall=False)
    assert results and isinstance(results, list)
    rec = results[0]
    # Deve salvar arquivo .html
    assert rec['fulltext_path'].endswith('.html')
    # Conteúdo extraído deve conter texto limpo
    assert 'Hello world!' in rec['full_text']

def test_fetch_fulltext_pdf(tmp_path, monkeypatch):
    # Prepara um registro com URL de PDF
    records = [{'Download URL': 'http://example.com/test.pdf', 'DOI': '10.1234/testpdf'}]
    pdf_bytes = b'%PDF-1.4 Dummy PDF content'
    import revsys.fulltext as ftmod
    # Monkeypatch de requests.get para retornar PDF
    monkeypatch.setattr(ftmod.requests, 'get', lambda url, stream=True, **kw: FakeResponse(content=pdf_bytes))
    # Monkeypatch pdfminer disponível e extract_text
    monkeypatch.setattr(ftmod, '_PDFMINER_AVAILABLE', True)
    monkeypatch.setattr(ftmod, 'extract_text', lambda path: 'Extracted PDF text')

    results = fetch_fulltext(records, str(tmp_path), use_unpaywall=False)
    rec = results[0]
    # Deve salvar arquivo .pdf
    assert rec['fulltext_path'].endswith('.pdf')
    # Texto extraído deve vir do extract_text
    assert rec['full_text'] == 'Extracted PDF text'