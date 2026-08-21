from pathlib import Path

from document_extractor import extract_pdf_text

ROOT = Path(__file__).resolve().parent.parent


def test_extract_returns_text():
    text = extract_pdf_text(ROOT / "08_proof_of_delivery.pdf")
    assert isinstance(text, str)
    assert len(text) > 0


def test_extract_contains_pod_keywords():
    text = extract_pdf_text(ROOT / "08_proof_of_delivery.pdf")
    # Key terms the POD parser depends on must be present
    assert "58" in text
    assert "60" in text
