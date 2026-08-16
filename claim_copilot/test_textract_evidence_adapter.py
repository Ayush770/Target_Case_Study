from textract_evidence_adapter import parse_inspection_report


sample_text = """
INDEPENDENT CARGO INSPECTION REPORT

Observed shipment condition

Five cartons showed crush, puncture and/or moisture damage.

TOTAL: 20 units examined; 14 unsellable; 6 functional but require repacking.

Cost documentation supplied by Northstar

Inspection fee: $420.00 Repack labor: $300.00
"""


facts = parse_inspection_report(sample_text)


for fact in facts:
    print(fact)


assert len(facts) == 5

assert any(
    fact.id == "fact.inspection_damaged_cartons"
    and fact.value == "5"
    for fact in facts
)

assert any(
    fact.id == "fact.inspection_unsellable_units"
    and fact.value == "14"
    for fact in facts
)

assert any(
    fact.id == "fact.inspection_repackable_units"
    and fact.value == "6"
    for fact in facts
)

assert any(
    fact.id == "fact.inspection_cost"
    and fact.value == "420.00"
    for fact in facts
)

assert any(
    fact.id == "fact.repack_labor"
    and fact.value == "300.00"
    for fact in facts
)


print("Textract evidence adapter test passed.")