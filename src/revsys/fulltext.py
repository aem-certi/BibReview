"""
Módulo para download e extração de texto completo de artigos.
"""
import os
import json
import requests
from pathlib import Path
from revsys.config import OPENALEX_EMAIL
import logging

# Suprimir avisos de CropBox do pdfminer
logging.getLogger('pdfminer').setLevel(logging.ERROR)
logging.getLogger('pdfminer.pdfpage').setLevel(logging.ERROR)

__all__ = ['fetch_fulltext']

# Tenta importar função de extração de texto de PDF
try:
    from pdfminer.high_level import extract_text
    _PDFMINER_AVAILABLE = True
except ImportError:
    _PDFMINER_AVAILABLE = False

def fetch_fulltext(
    records: list[dict],
    output_dir: str,
    use_unpaywall: bool = True
) -> list[dict]:
    """
    Para cada registro com DOI ou Download URL, baixa o PDF e extrai texto.

    Args:
        records: lista de dicionários contendo 'DOI' e/ou 'Download URL'.
        output_dir: diretório onde serão salvos os PDFs.
        use_unpaywall: se True, tenta Unpaywall API para obter URL de PDF de OA.

    Returns:
        Lista de registros atualizados com campos:
            'fulltext_path': caminho local do PDF ou None
            'full_text': texto extraído ou ''
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    email = OPENALEX_EMAIL or ''
    for rec in records:
        # Load raw URL and normalize to string
        raw_url = rec.get('Download URL') or rec.get('DownloadURL') or ''
        pdf_url = ''
        if raw_url is not None:
            pdf_url = str(raw_url).strip()
        # Treat NaN string as missing
        if pdf_url.lower() == 'nan':
            pdf_url = ''
        # Normalize DOI to string, skip if NaN
        doi_raw = rec.get('DOI', '')
        doi_str = str(doi_raw).strip()
        doi = doi_str if doi_str.lower() != 'nan' else ''
        # Se não tiver URL e usar Unpaywall, tenta obter
        if use_unpaywall and not pdf_url and doi:
            try:
                api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
                resp = requests.get(api_url, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    loc = data.get('best_oa_location') or {}
                    pdf_url = loc.get('url_for_pdf', '')
            except Exception:
                pdf_url = ''
        fulltext_path = None
        text = ''
        if pdf_url:
            # Determine base name: prefer DOI, fallback to ID, else 'file'
            doi_raw = rec.get('DOI', '')
            doi_str = str(doi_raw).strip()
            if not doi_str or doi_str.lower() == 'nan':
                id_raw = rec.get('ID', '')
                id_str = str(id_raw).strip()
                base = id_str if id_str and id_str.lower() != 'nan' else 'file'
            else:
                base = doi_str
            # Sanitize base: keep alphanumeric, underscore, hyphen
            fname = ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in base)
            # Determine URL and extension (ensure string)
            url = str(pdf_url).strip()
            ext = os.path.splitext(url)[1].lower()
            # XML/JATS/HTML
            if ext in ('.xml', '.nxml', '.html', '.htm'):
                xml_path = out_dir / f"{fname}{ext}"
                try:
                    r = requests.get(url, timeout=60)
                    r.raise_for_status()
                    with open(xml_path, 'wb') as f:
                        f.write(r.content)
                    fulltext_path = str(xml_path)
                    # Extrair texto bruto do XML/HTML
                    try:
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(r.content)
                        text = ''.join(root.itertext())
                    except Exception:
                        text = ''
                except Exception:
                    fulltext_path = None
                    text = ''
            else:
                # Tratamento padrão PDF
                pdf_path = out_dir / f"{fname}.pdf"
                try:
                    r = requests.get(url, stream=True, timeout=60)
                    r.raise_for_status()
                    with open(pdf_path, 'wb') as f:
                        for chunk in r.iter_content(1024):
                            f.write(chunk)
                    fulltext_path = str(pdf_path)
                    # Extrair texto se possível
                    if _PDFMINER_AVAILABLE:
                        try:
                            text = extract_text(fulltext_path)
                        except Exception:
                            text = ''
                except Exception:
                    fulltext_path = None
                    text = ''
        rec['fulltext_path'] = fulltext_path
        rec['full_text'] = text
        results.append(rec)
    return results