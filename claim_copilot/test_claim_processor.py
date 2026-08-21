"""Integration test for claim_processor.process_claim.

Runs the full pipeline against local fixture files.
AWS services (S3, Textract) are intentionally absent; both code paths
have graceful fallbacks so this test must pass without credentials.
"""
from claim_processor import process_claim


def test_process_claim_returns_expected_keys():
    result = process_claim("CLAIM-001")

    assert result["claim_id"] == "CLAIM-001"
    assert "evidence" in result
    assert "reconciliation" in result
    assert "contract_position" in result
    assert "historical_comparables" in result


def test_evidence_has_facts():
    result = process_claim("CLAIM-001")
    facts = result["evidence"].get_all_facts()
    assert len(facts) > 0


def test_reconciliation_finds_mismatch():
    result = process_claim("CLAIM-001")
    # EDI=59 vs POD=58 — mismatch must be detected
    assert result["reconciliation"] is not None
    assert result["reconciliation"].id == "COUNT_MISMATCH"


def test_contract_positions_produced():
    result = process_claim("CLAIM-001")
    assert len(result["contract_position"]) > 0


def test_historical_comparables_produced():
    result = process_claim("CLAIM-001")
    assert len(result["historical_comparables"]) > 0
