import csv
import json
from decimal import Decimal
from pathlib import Path

import pytest

from contract_engine import (
    cargo_liability_cap,
    inspection_cost_position,
    repack_labor_position,
    delay_position,
)

# Resolve fixture paths relative to this file so tests pass regardless of
# the working directory pytest is invoked from.
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def erp():
    with open(ROOT / "05_erp_order_invoice.csv", newline="") as f:
        return next(csv.DictReader(f))


@pytest.fixture(scope="module")
def tms():
    with open(ROOT / "04_tms_shipment.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def cargo_values(erp):
    unit_price = Decimal(erp["unit_price_usd"])
    unsellable_units = Decimal("14")
    missing_units = Decimal("8")
    direct_cargo_value = (missing_units + unsellable_units) * unit_price
    affected_weight_lbs = (missing_units + unsellable_units) * Decimal("15")
    return {
        "unit_price": unit_price,
        "direct_cargo_value": direct_cargo_value,
        "affected_weight_lbs": affected_weight_lbs,
    }


def test_cargo_liability_cap(cargo_values):
    result = cargo_liability_cap(
        invoice_value=cargo_values["direct_cargo_value"],
        affected_weight_lbs=cargo_values["affected_weight_lbs"],
    )
    assert result.id == "CARGO_LIABILITY"
    assert result.clause == "Section 2"
    assert result.amount == "$9,350.00"
    assert result.status == "contractually_supported"


def test_inspection_cost_position():
    result = inspection_cost_position(inspection_cost=Decimal("420.00"))
    assert result.id == "INSPECTION_COST"
    assert result.clause == "Section 3"
    assert result.status == "potentially_recoverable"
    assert result.amount == "$420.00"


def test_repack_labor_position():
    result = repack_labor_position(repack_cost=Decimal("300.00"))
    assert result.id == "REPACK_LABOR"
    assert result.clause == "Section 3"
    assert result.status == "requires_support"
    assert result.amount == "$300.00"


def test_delay_position_no_guarantee():
    result = delay_position(
        requested_amount=Decimal("18000.00"),
        guaranteed_service=False,
    )
    assert result.id == "DELAY"
    assert result.clause == "Section 4"
    assert result.status == "commercial_only"


def test_delay_position_with_guarantee():
    result = delay_position(
        requested_amount=Decimal("18000.00"),
        guaranteed_service=True,
    )
    assert result.id == "DELAY"
    assert result.clause == "Section 4"
    assert result.status == "potentially_contractual"


def test_delay_position_none_guarantee():
    # guaranteed_service=None (field absent in TMS) must not raise
    result = delay_position(
        requested_amount=Decimal("18000.00"),
        guaranteed_service=None,
    )
    assert result.id == "DELAY"
    assert result.status == "commercial_only"
