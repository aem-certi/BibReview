import pytest

from revsys.utils import clean_text, format_vancouver_authors, format_vancouver_reference

def test_clean_text_basic():
    # Should remove '!' but retain periods
    assert clean_text(" Hello! World... ") == "hello world..."
    assert clean_text("ÁéÍóú!!!") == "aeiou"

def test_format_vancouver_authors_less():
    assert format_vancouver_authors(["Silva JA"]) == "Silva JA"
    assert format_vancouver_authors(["Silva JA", "Souza MR"]) == "Silva JA, Souza MR"

def test_format_vancouver_authors_more():
    authors = [f"Author{i}" for i in range(1, 8)]
    res = format_vancouver_authors(authors, max_authors=6)
    parts = res.split(', ')
    assert parts[-1] == 'et al.'
    assert len(parts) == 7

def test_format_vancouver_reference_full():
    authors = ["Silva JA", "Souza MR"]
    ref = format_vancouver_reference(
        authors, "Título Teste", "Journal X", "2023", volume="15", issue="3", pages="100-110"
    )
    assert "Silva JA, Souza MR" in ref
    assert "Título Teste" in ref
    assert "Journal X" in ref
    assert "2023;15(3):100-110." in ref

def test_format_vancouver_reference_minimal():
    ref = format_vancouver_reference([], "T", "J", "2023")
    assert ref.endswith('.')

if __name__ == '__main__':
    pytest.main()