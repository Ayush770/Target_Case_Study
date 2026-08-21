import json
from pathlib import Path

from evidence import create_fact
from reconciliation import reconcile_delivery_counts, finding_to_dict

ROOT = Path(__file__).resolve().parent.parent


def _edi_fact(value: str):
    return create_fact(
        fact_id="fact.edi_delivered_pieces",
        label="Pieces delivered (EDI)",
        value=value,
        source_file="04_tms_shipment.json",
        locator="events[DELIVERED].pieces",
        source_role="carrier_operational_record",
        status="disputed",
    )


def _pod_fact(value: str):
    return create_fact(
        fact_id="fact.pod_received_cartons",
        label="Cartons received (signed POD)",
        value=value,
        source_file="08_proof_of_delivery.pdf",
        locator="page 1; Received 58 of 60 cartons",
        source_role="consignee_signed_receipt",
    )


def test_mismatch_produces_finding():
    finding = reconcile_delivery_counts(_edi_fact("59"), _pod_fact("58"))

    assert finding is not None
    result = finding_to_dict(finding)

    assert result["id"] == "COUNT_MISMATCH"
    assert result["severity"] == "high"
    assert result["status"] == "open"
    assert "fact.edi_delivered_pieces" in result["facts"]
    assert "fact.pod_received_cartons" in result["facts"]


def test_matching_counts_returns_none():
    assert reconcile_delivery_counts(_edi_fact("58"), _pod_fact("58")) is None


def test_uses_fixture_edi_value():
    with open(ROOT / "04_tms_shipment.json") as f:
        tms = json.load(f)

    delivered_event = next(e for e in tms["events"] if e["code"] == "DELIVERED")
    finding = reconcile_delivery_counts(
        _edi_fact(str(delivered_event["pieces"])),
        _pod_fact("58"),
    )
    assert finding is not None
    assert finding.id == "COUNT_MISMATCH"
