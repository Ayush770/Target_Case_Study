from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation

try:
    from .evidence import EvidenceFact
except ImportError:  # pragma: no cover - script-style execution fallback
    from evidence import EvidenceFact


@dataclass(frozen=True)
class ReconciliationFinding:
    id: str
    severity: str
    status: str
    title: str
    detail: str
    fact_ids: list[str]


def _numeric_value(fact: EvidenceFact) -> Decimal:
    try:
        return Decimal(fact.value)
    except (InvalidOperation, TypeError):
        raise ValueError(
            f"Fact '{fact.id}' must contain a numeric value, "
            f"received: {fact.value!r}"
        )


def reconcile_delivery_counts(
    edi_fact: EvidenceFact,
    pod_fact: EvidenceFact,
) -> ReconciliationFinding | None:
    """
    Compare the carrier EDI delivered quantity against
    the consignee-signed POD received quantity.

    Values are read from EvidenceFact objects; no claim-specific
    quantities are hardcoded here.
    """

    edi_value = _numeric_value(edi_fact)
    pod_value = _numeric_value(pod_fact)

    if edi_value == pod_value:
        return None

    return ReconciliationFinding(
        id="COUNT_MISMATCH",
        severity="high",
        status="open",
        title="Delivery count conflict",
        detail=(
            f"Carrier EDI reports {edi_value} pieces delivered, "
            f"while the signed POD records {pod_value} cartons received."
        ),
        fact_ids=[
            edi_fact.id,
            pod_fact.id,
        ],
    )


def finding_to_dict(
    finding: ReconciliationFinding,
) -> dict:
    return asdict(finding)