import json
from pathlib import Path

from tms_evidence_adapter import parse_tms_delivery_fact

ROOT = Path(__file__).resolve().parent.parent


def test_edi_delivered_pieces_extracted():
    with open(ROOT / "04_tms_shipment.json") as f:
        tms = json.load(f)

    facts = parse_tms_delivery_fact(tms)

    assert len(facts) >= 1
    assert facts[0].id == "fact.edi_delivered_pieces"
    assert facts[0].value == "59"


def test_fact_has_anchor():
    with open(ROOT / "04_tms_shipment.json") as f:
        tms = json.load(f)

    facts = parse_tms_delivery_fact(tms)
    assert facts[0].anchors[0].source_role == "carrier_edi"


def test_no_delivered_event_returns_empty():
    facts = parse_tms_delivery_fact({"events": []})
    assert facts == []
