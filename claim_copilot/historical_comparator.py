from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class ComparatorWeights:
    carrier: Decimal = Decimal("0.35")
    service_level: Decimal = Decimal("0.20")
    issue_overlap: Decimal = Decimal("0.15")
    evidence_overlap: Decimal = Decimal("0.10")
    amount_proximity: Decimal = Decimal("0.10")
    context_match: Decimal = Decimal("0.10")


@dataclass(frozen=True)
class HistoricalComparison:
    claim_id: str
    issue_type: str
    claimed: str
    settled: str
    settlement_pct: str
    evidence: str
    summary: str
    notes: str
    score: Decimal
    reasons: list[str]


def load_historical_claims(csv_path: str | Path) -> list[dict[str, str]]:
    with Path(csv_path).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _tokens(value: str) -> set[str]:
    return {
        token.strip().lower()
        for token in value.replace(",", "+").split("+")
        if token.strip()
    }


def _overlap(
    current: set[str],
    historical: set[str],
) -> Decimal:
    union = current | historical

    if not union:
        return Decimal("0")

    return Decimal(len(current & historical)) / Decimal(len(union))


def _amount_proximity(
    current_amount: Decimal,
    historical_amount: Decimal,
) -> Decimal:
    denominator = max(current_amount, historical_amount)

    if denominator == 0:
        return Decimal("1")

    difference = abs(current_amount - historical_amount)

    return max(
        Decimal("0"),
        Decimal("1") - difference / denominator,
    )


def _same_context(
    current_notes: str,
    historical_notes: str,
) -> bool:
    current = current_notes.lower()
    historical = historical_notes.lower()

    return (
        "no guaranteed service" in current
        and "no guaranteed service" in historical
    )


def compare_claim(
    current_claim: dict[str, str],
    historical_claim: dict[str, str],
    weights: ComparatorWeights | None = None,
) -> HistoricalComparison:
    weights = weights or ComparatorWeights()

    score = Decimal("0")
    reasons: list[str] = []

    # Carrier
    if current_claim["carrier"] == historical_claim["carrier"]:
        score += weights.carrier
        reasons.append("same carrier")

    # Service level
    if current_claim["service_level"] == historical_claim["service_level"]:
        score += weights.service_level
        reasons.append("same service level")

    # Issue overlap
    current_issues = _tokens(current_claim["issue_type"])
    historical_issues = _tokens(historical_claim["issue_type"])

    issue_overlap = _overlap(
        current_issues,
        historical_issues,
    )

    score += weights.issue_overlap * issue_overlap

    if issue_overlap > 0:
        matched = sorted(current_issues & historical_issues)
        reasons.append(
            f"issue overlap: {', '.join(matched)}"
        )

    # Evidence overlap
    current_evidence = _tokens(current_claim["evidence"])
    historical_evidence = _tokens(historical_claim["evidence"])

    evidence_overlap = _overlap(
        current_evidence,
        historical_evidence,
    )

    score += weights.evidence_overlap * evidence_overlap

    if evidence_overlap > 0:
        matched = sorted(current_evidence & historical_evidence)
        reasons.append(
            f"evidence overlap: {', '.join(matched)}"
        )

    # Claim amount proximity
    current_amount = Decimal(current_claim["claimed_usd"])
    historical_amount = Decimal(historical_claim["claimed_usd"])

    amount_score = _amount_proximity(
        current_amount,
        historical_amount,
    )

    score += weights.amount_proximity * amount_score

    if amount_score >= Decimal("0.66"):
        reasons.append("similar claim amount")

    # Contract/service context
    if _same_context(
        current_claim.get("notes", ""),
        historical_claim.get("notes", ""),
    ):
        score += weights.context_match
        reasons.append("same non-guaranteed service context")

    return HistoricalComparison(
        claim_id=historical_claim["claim_id"],
        issue_type=historical_claim["issue_type"],
        claimed=f"${Decimal(historical_claim['claimed_usd']):,.2f}",
        settled=f"${Decimal(historical_claim['settled_usd']):,.2f}",
        settlement_pct=(
            f"{Decimal(historical_claim['settlement_pct']) * 100:.1f}%"
        ),
        evidence=historical_claim["evidence"],
        summary=historical_claim["negotiation_summary"],
        notes=historical_claim["notes"],
        score=score.quantize(Decimal("0.001")),
        reasons=reasons,
    )


def find_comparables(
    current_claim: dict[str, str],
    historical_claims: list[dict[str, str]],
    limit: int = 5,
    weights: ComparatorWeights | None = None,
) -> list[HistoricalComparison]:
    """
    Deterministic filtering first, explainable scoring second.

    Historical claims are negotiation context only.
    They are not treated as predictions or legal entitlements.
    """

    candidates = [
        claim
        for claim in historical_claims
        if claim["carrier"] == current_claim["carrier"]
        and claim["service_level"] == current_claim["service_level"]
    ]

    ranked = [
        compare_claim(
            current_claim=current_claim,
            historical_claim=claim,
            weights=weights,
        )
        for claim in candidates
    ]

    ranked.sort(
        key=lambda result: result.score,
        reverse=True,
    )

    return ranked[:limit]


def comparison_to_dict(
    comparison: HistoricalComparison,
) -> dict:
    return asdict(comparison)