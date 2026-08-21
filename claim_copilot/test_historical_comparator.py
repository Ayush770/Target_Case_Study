import json
from pathlib import Path

from historical_comparator import load_historical_claims, find_comparables

ROOT = Path(__file__).resolve().parent.parent


def _current_claim(snapshot, tms):
    service = tms["service"]
    return {
        "carrier": snapshot["carrier"],
        "service_level": service["name"],
        "claimed_usd": str(snapshot["claim_amount_usd"]),
        "issue_type": "DAMAGE+SHORTAGE+DELAY",
        "evidence": "POD+INSPECTION+PHOTOS",
        "notes": (
            "No guaranteed service"
            if not service["guaranteed"]
            else "Guaranteed service"
        ),
    }


def test_comparables_returned():
    with open(ROOT / "03_claim_snapshot.json") as f:
        snapshot = json.load(f)
    with open(ROOT / "04_tms_shipment.json") as f:
        tms = json.load(f)

    historical = load_historical_claims(ROOT / "12_historical_claims.csv")
    results = find_comparables(_current_claim(snapshot, tms), historical, limit=5)

    assert len(results) > 0


def test_scores_in_range():
    with open(ROOT / "03_claim_snapshot.json") as f:
        snapshot = json.load(f)
    with open(ROOT / "04_tms_shipment.json") as f:
        tms = json.load(f)

    historical = load_historical_claims(ROOT / "12_historical_claims.csv")
    results = find_comparables(_current_claim(snapshot, tms), historical)

    for r in results:
        assert 0 <= float(r.score) <= 1


def test_sorted_descending():
    with open(ROOT / "03_claim_snapshot.json") as f:
        snapshot = json.load(f)
    with open(ROOT / "04_tms_shipment.json") as f:
        tms = json.load(f)

    historical = load_historical_claims(ROOT / "12_historical_claims.csv")
    results = find_comparables(_current_claim(snapshot, tms), historical)

    scores = [float(r.score) for r in results]
    assert scores == sorted(scores, reverse=True)
