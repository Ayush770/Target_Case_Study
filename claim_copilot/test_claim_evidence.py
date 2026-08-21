from claim_evidence import ClaimEvidence
from evidence import EvidenceFact, EvidenceAnchor


def _make_pod_fact():
    return EvidenceFact(
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


def _make_inspection_fact():
    return EvidenceFact(
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


def test_add_and_retrieve_facts():
    claim = ClaimEvidence(claim_id="CLAIM-001")
    claim.add_facts([_make_pod_fact(), _make_inspection_fact()])

    assert len(claim.get_all_facts()) == 2
    assert claim.get_fact("fact.pod_received_cartons").value == "58"
    assert claim.get_fact("fact.inspection_unsellable_units").value == "14"


def test_source_files_traceability():
    claim = ClaimEvidence(claim_id="CLAIM-001")
    claim.add_facts([_make_pod_fact(), _make_inspection_fact()])

    sources = claim.source_files()

    assert "08_proof_of_delivery.pdf" in sources
    assert "09_damage_inspection_report_scanned.pdf" in sources


def test_get_fact_missing_returns_none():
    claim = ClaimEvidence(claim_id="CLAIM-001")
    assert claim.get_fact("fact.nonexistent") is None
