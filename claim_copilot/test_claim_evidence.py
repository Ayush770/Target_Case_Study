from claim_evidence import ClaimEvidence
from evidence import EvidenceFact, EvidenceAnchor


# Mock facts coming from existing adapters:
# POD parser
# Textract adapter
# TMS parser
# ERP parser


pod_fact = EvidenceFact(
    id="fact.pod_received_cartons",
    label="Cartons received",
    value="58",
    status="verified",
    anchors=[
        EvidenceAnchor(
            file="08_proof_of_delivery.pdf",
            locator="Received 58 of 60 cartons",
            source_role="consignee_signed_receipt",
            confidence=0.99,
        )
    ],
)


inspection_fact = EvidenceFact(
    id="fact.inspection_unsellable_units",
    label="Unsellable units",
    value="14",
    status="verified",
    anchors=[
        EvidenceAnchor(
            file="09_damage_inspection_report_scanned.pdf",
            locator="TOTAL: 20 units examined; 14 unsellable",
            source_role="inspection_report",
            confidence=0.95,
        )
    ],
)


# Create unified claim evidence

claim = ClaimEvidence(
    claim_id="CLAIM-001"
)


claim.add_facts(
    [
        pod_fact,
        inspection_fact,
    ]
)


# Validate facts

assert len(claim.get_all_facts()) == 2


assert (
    claim.get_fact(
        "fact.pod_received_cartons"
    ).value
    == "58"
)


assert (
    claim.get_fact(
        "fact.inspection_unsellable_units"
    ).value
    == "14"
)


# Validate source traceability

sources = claim.source_files()

assert "08_proof_of_delivery.pdf" in sources

assert (
    "09_damage_inspection_report_scanned.pdf"
    in sources
)


print("Claim evidence aggregation test passed.")

print("\nSources:")
for source in sources:
    print(source)


print("\nFacts:")
for fact in claim.get_all_facts():
    print(fact)