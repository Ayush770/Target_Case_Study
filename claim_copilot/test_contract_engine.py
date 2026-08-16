import csv
import json
from decimal import Decimal

from contract_engine import (
    cargo_liability_cap,
    inspection_cost_position,
    repack_labor_position,
    delay_position,
)


# ---- Load case data from source files ----

with open("../05_erp_order_invoice.csv", newline="") as file:
    erp = next(csv.DictReader(file))

with open("../04_tms_shipment.json") as file:
    tms = json.load(file)


# ---- Derive values from source evidence ----

unit_price = Decimal(erp["unit_price_usd"])

unsellable_units = Decimal("14")
missing_units = Decimal("8")

direct_cargo_value = (
    missing_units * unit_price
    + unsellable_units * unit_price
)

affected_units = missing_units + unsellable_units

# Product-weight proxy used by the supplied case logic.
affected_weight_lbs = affected_units * Decimal("15")


# ---- Section 2: Cargo liability ----

cargo = cargo_liability_cap(
    invoice_value=direct_cargo_value,
    affected_weight_lbs=affected_weight_lbs,
)

print(cargo)

assert cargo.id == "CARGO_LIABILITY"
assert cargo.clause == "Section 2"
assert cargo.amount == "$9,350.00"


# ---- Section 3: Inspection ----

inspection = inspection_cost_position(
    inspection_cost=Decimal("420.00"),
)

print(inspection)

assert inspection.id == "INSPECTION_COST"
assert inspection.clause == "Section 3"
assert inspection.status == "potentially_recoverable"


# ---- Section 3: Repack labor ----

repack = repack_labor_position(
    repack_cost=Decimal("300.00"),
)

print(repack)

assert repack.id == "REPACK_LABOR"
assert repack.clause == "Section 3"
assert repack.status == "requires_support"


# ---- Section 4: Delay without Guaranteed Appointment ----

delay = delay_position(
    requested_amount=Decimal("18000.00"),
    guaranteed_service=False,
)

print(delay)

assert delay.id == "DELAY"
assert delay.clause == "Section 4"
assert delay.status == "commercial_only"


print("Contract engine test passed.")