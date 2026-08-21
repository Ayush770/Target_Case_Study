from pathlib import Path

import pytest

from document_extractor import extract_pdf_text
from pod_parser import parse_pod

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def pod_facts():
    text = extract_pdf_text(ROOT / "08_proof_of_delivery.pdf")
    return parse_pod(text)


def test_four_facts_extracted(pod_facts):
    assert len(pod_facts) == 4


def test_received_cartons(pod_facts):
    values = {f.id: f.value for f in pod_facts}
    assert values["fact.pod_received_cartons"] == "58"


def test_tendered_cartons(pod_facts):
    values = {f.id: f.value for f in pod_facts}
    assert values["fact.pod_tendered_cartons"] == "60"


def test_short_cartons(pod_facts):
    values = {f.id: f.value for f in pod_facts}
    assert values["fact.pod_short_cartons"] == "2"


def test_damaged_cartons(pod_facts):
    values = {f.id: f.value for f in pod_facts}
    assert values["fact.pod_damaged_cartons"] == "5"
