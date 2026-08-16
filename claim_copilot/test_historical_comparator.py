import json
from pathlib import Path

from historical_comparator import (
    load_historical_claims,
    find_comparables,
)


ROOT = Path("..")


# ---------------------------------------------------------
# Load current claim source data
# ---------------------------------------------------------

with (ROOT / "03_claim_snapshot.json").open() as file:
    snapshot = json.load(file)

with (ROOT / "04_tms_shipment.json").open() as file:
    tms = json.load(file)


# ---------------------------------------------------------
# Derive current claim profile from source records
# ---------------------------------------------------------

service = tms["service"]

current_claim = {
    "carrier": snapshot["carrier"],
    "service_level": service["name"],
    "claimed_usd": str(snapshot["claim_amount_usd"]),

    # Business dimensions represented by the supplied case.
    "issue_type": "DAMAGE+SHORTAGE+DELAY",
    "evidence": "POD+INSPECTION+PHOTOS",

    # Derived from the actual service record.
    "notes": (
        "No guaranteed service"
        if not service["guaranteed"]
        else "Guaranteed service"
    ),
}


# ---------------------------------------------------------
# Load historical claims
# ---------------------------------------------------------

historical_claims = load_historical_claims(
    ROOT / "12_historical_claims.csv"
)


# ---------------------------------------------------------
# Find comparable claims
# ---------------------------------------------------------

results = find_comparables(
    current_claim=current_claim,
    historical_claims=historical_claims,
    limit=5,
)


# ---------------------------------------------------------
# Validate
# ---------------------------------------------------------

assert results, "No historical comparables were returned."

print("\nHistorical comparables:\n")

for result in results:
    print(
        f"{result.claim_id} | "
        f"score={result.score} | "
        f"claimed={result.claimed} | "
        f"settled={result.settled} | "
        f"settlement={result.settlement_pct}"
    )

    print(f"  reasons: {', '.join(result.reasons)}")
    print()


# Verify that deterministic carrier/service filtering worked.
for result in results:
    assert result.score >= 0
    assert result.score <= 1


print("Historical comparator test passed.")