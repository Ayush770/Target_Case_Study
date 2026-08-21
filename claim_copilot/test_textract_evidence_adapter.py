from textract_evidence_adapter import parse_inspection_report

SAMPLE_TEXT = """
INDEPENDENT CARGO INSPECTION REPORT

Observed shipment condition

Five cartons showed crush, puncture and/or moisture damage.

TOTAL: 20 units examined; 14 unsellable; 6 functional but require repacking.

Cost documentation supplied by Northstar

Inspection fee: $420.00 Repack labor: $300.00
"""


def test_parse_returns_five_facts():
    facts = parse_inspection_report(SAMPLE_TEXT)
    assert len(facts) == 5


def test_damaged_cartons():
    facts = parse_inspection_report(SAMPLE_TEXT)
    match = next(f for f in facts if f.id == "fact.inspection_damaged_cartons")
    assert match.value == "5"


def test_unsellable_units():
    facts = parse_inspection_report(SAMPLE_TEXT)
    match = next(f for f in facts if f.id == "fact.inspection_unsellable_units")
    assert match.value == "14"


def test_repackable_units():
    facts = parse_inspection_report(SAMPLE_TEXT)
    match = next(f for f in facts if f.id == "fact.inspection_repackable_units")
    assert match.value == "6"


def test_inspection_cost():
    facts = parse_inspection_report(SAMPLE_TEXT)
    match = next(f for f in facts if f.id == "fact.inspection_cost")
    assert match.value == "420.00"


def test_repack_labor():
    facts = parse_inspection_report(SAMPLE_TEXT)
    match = next(f for f in facts if f.id == "fact.repack_labor")
    assert match.value == "300.00"
