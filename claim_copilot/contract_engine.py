from dataclasses import dataclass, asdict
from decimal import Decimal


CARGO_LIABILITY_PER_POUND = Decimal("50.00")


@dataclass(frozen=True)
class ContractPosition:
    id: str
    amount: str
    status: str
    clause: str
    rationale: str


def cargo_liability_cap(
    invoice_value: Decimal,
    affected_weight_lbs: Decimal,
) -> ContractPosition:
    weight_based_limit = (
        affected_weight_lbs * CARGO_LIABILITY_PER_POUND
    )

    contractual_limit = min(
        invoice_value,
        weight_based_limit,
    )

    return ContractPosition(
        id="CARGO_LIABILITY",
        amount=f"${contractual_limit:,.2f}",
        status="contractually_supported",
        clause="Section 2",
        rationale=(
            f"Liability is the lesser of invoice value "
            f"(${invoice_value:,.2f}) and the contractual "
            f"weight limit (${weight_based_limit:,.2f})."
        ),
    )


def inspection_cost_position(
    inspection_cost: Decimal,
) -> ContractPosition:
    return ContractPosition(
        id="INSPECTION_COST",
        amount=f"${inspection_cost:,.2f}",
        status="potentially_recoverable",
        clause="Section 3",
        rationale=(
            "Reasonable third-party inspection costs may be "
            "considered when requested or reasonably necessary "
            "to establish the loss."
        ),
    )


def repack_labor_position(
    repack_cost: Decimal,
) -> ContractPosition:
    return ContractPosition(
        id="REPACK_LABOR",
        amount=f"${repack_cost:,.2f}",
        status="requires_support",
        clause="Section 3",
        rationale=(
            "Internal administrative labor is not separately "
            "reimbursable unless agreed in writing."
        ),
    )


def delay_position(
    requested_amount: Decimal,
    guaranteed_service: bool | None,
) -> ContractPosition:
    if guaranteed_service:
        return ContractPosition(
            id="DELAY",
            amount=f"${requested_amount:,.2f}",
            status="potentially_contractual",
            clause="Section 4",
            rationale=(
                "A written Guaranteed Appointment service "
                "may permit a service refund when the confirmed "
                "appointment was missed for reasons within "
                "carrier control."
            ),
        )

    return ContractPosition(
        id="DELAY",
        amount=f"${requested_amount:,.2f}",
        status="commercial_only",
        clause="Section 4",
        rationale=(
            "Standard LTL dates are estimates. Delay-related "
            "markdowns, promotion value, lost profits and "
            "other consequential damages are excluded."
        ),
    )


def position_to_dict(
    position: ContractPosition,
) -> dict:
    return asdict(position)