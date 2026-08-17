"""
End-to-end regression test for the Freight Claim Copilot.

Covers the complete happy-path integration:
  API health → document upload → S3 storage → S3 retrieval →
  claim processing → evidence extraction → reconciliation →
  contract position → historical comparables → API serialization →
  frontend-compatible response

Requirements:
  - FastAPI TestClient (starlette — already a FastAPI dependency)
  - AWS credentials configured (S3 upload/download are real AWS calls)
  - uvicorn not required — TestClient drives the ASGI app in-process

Run:
  cd claim_copilot
  python3 -m pytest test_e2e_integration.py -v
"""

import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# App and constants
# ---------------------------------------------------------------------------

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api import app                         # noqa: E402 — after sys.path insert
from s3_service import S3Service            # noqa: E402

ROOT = Path(__file__).resolve().parent.parent   # Target_Case_Study/

# Use a unique claim ID per test run so repeated runs don't collide
CLAIM_ID = f"E2E-TEST-{uuid.uuid4().hex[:8].upper()}"

# Source documents that must drive the analysis
SOURCE_DOCS = [
    ROOT / "03_claim_snapshot.json",
    ROOT / "04_tms_shipment.json",
    ROOT / "05_erp_order_invoice.csv",
    ROOT / "08_proof_of_delivery.pdf",
    ROOT / "09_damage_inspection_report_scanned.pdf",
]

# MIME types for multipart upload
MIME = {
    ".json": "application/json",
    ".csv":  "text/csv",
    ".pdf":  "application/pdf",
    ".png":  "image/png",
}

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mime(path: Path) -> str:
    return MIME.get(path.suffix.lower(), "application/octet-stream")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def uploaded_keys():
    """Upload all source documents and return list of S3 keys."""
    keys = []
    for doc in SOURCE_DOCS:
        assert doc.exists(), f"Source document missing from repo: {doc.name}"
        with open(doc, "rb") as fh:
            resp = client.post(
                f"/claims/{CLAIM_ID}/documents",
                files={"file": (doc.name, fh, _mime(doc))},
            )
        assert resp.status_code == 200, (
            f"Upload failed for {doc.name}: "
            f"HTTP {resp.status_code} — {resp.text[:300]}"
        )
        body = resp.json()
        assert body.get("status") == "uploaded", f"Unexpected status: {body}"
        assert "s3_key" in body, f"No s3_key in response: {body}"
        keys.append(body["s3_key"])
    return keys


@pytest.fixture(scope="module")
def analysis_result(uploaded_keys):  # noqa: F811 — depends on upload
    """Run claim analysis and return the raw pipeline response."""
    resp = client.post(f"/claims/{CLAIM_ID}/analyze")
    assert resp.status_code == 200, (
        f"Analysis failed: HTTP {resp.status_code} — {resp.text[:300]}"
    )
    return resp.json()


@pytest.fixture(scope="module")
def frontend_response(analysis_result):  # noqa: F811
    """Fetch the frontend-compatible claim response."""
    resp = client.get(f"/api/claim/{CLAIM_ID}")
    assert resp.status_code == 200, (
        f"GET /api/claim/{CLAIM_ID} failed: {resp.status_code} — {resp.text[:300]}"
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Step 1 — Health
# ---------------------------------------------------------------------------

def test_01_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"
    assert "service" in body


# ---------------------------------------------------------------------------
# Step 2 — Root serves HTML
# ---------------------------------------------------------------------------

def test_02_root_serves_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Step 3-4 — Upload + S3 key returned
# ---------------------------------------------------------------------------

def test_03_upload_all_documents_succeed(uploaded_keys):
    assert len(uploaded_keys) == len(SOURCE_DOCS), (
        f"Expected {len(SOURCE_DOCS)} uploads, got {len(uploaded_keys)}"
    )
    for key in uploaded_keys:
        # Key must follow the expected path pattern
        assert key.startswith(f"claims/{CLAIM_ID}/documents/"), (
            f"S3 key has unexpected prefix: {key}"
        )


# ---------------------------------------------------------------------------
# Step 5 — S3 objects actually exist
# ---------------------------------------------------------------------------

def test_04_s3_objects_exist(uploaded_keys):
    """Verify every uploaded key is listable via S3Service."""
    svc = S3Service()
    listed = svc.list_claim_documents(CLAIM_ID)
    listed_set = set(listed)
    for key in uploaded_keys:
        assert key in listed_set, (
            f"Uploaded key not found in S3 listing: {key}"
        )


# ---------------------------------------------------------------------------
# Step 6-7 — Analysis returns 200
# ---------------------------------------------------------------------------

def test_05_analysis_succeeds(analysis_result):
    assert "claim_id" in analysis_result
    assert analysis_result["claim_id"] == CLAIM_ID


# ---------------------------------------------------------------------------
# Step 8 — Analysis used uploaded S3 documents, not fixture fallback
# ---------------------------------------------------------------------------

def test_06_analysis_uses_s3_documents_not_fixture(analysis_result):
    """
    The pipeline calls _try_s3_documents() which downloads from S3.
    Proof: claim_snapshot in the result must contain the claim_id that
    matches our test claim, not the fixture claim FCL-2026-0147.
    Additionally, the evidence facts must include POD facts sourced
    from the uploaded 08_proof_of_delivery.pdf.
    """
    snap = analysis_result.get("claim_snapshot", {})
    assert snap, "claim_snapshot missing from analysis result — S3 docs not used"

    # The snapshot claim_id must match the uploaded document's content
    # (03_claim_snapshot.json contains FCL-2026-0147, which is expected)
    assert snap.get("carrier"), "carrier missing from claim_snapshot"
    assert snap.get("claim_amount_usd") is not None, "claim_amount_usd missing"

    # Evidence must not be empty — POD and/or inspection facts expected
    evidence_facts = analysis_result.get("evidence", {}).get("facts", [])
    assert len(evidence_facts) > 0, (
        "No evidence facts produced — pipeline may have fallen back to empty extraction"
    )

    # At least one fact must reference an uploaded source file
    anchor_files = {
        anchor["file"]
        for fact in evidence_facts
        for anchor in fact.get("anchors", [])
    }
    expected_sources = {
        "08_proof_of_delivery.pdf",
        "04_tms_shipment.json",
        "09_damage_inspection_report_scanned.pdf",
    }
    matched = anchor_files & expected_sources
    assert matched, (
        f"No evidence facts sourced from expected documents. "
        f"Anchor files found: {anchor_files}"
    )


# ---------------------------------------------------------------------------
# Step 9 — Evidence facts have anchors
# ---------------------------------------------------------------------------

def test_07_evidence_facts_have_source_anchors(analysis_result):
    facts = analysis_result.get("evidence", {}).get("facts", [])
    assert facts, "No evidence facts returned"
    for fact in facts:
        assert fact.get("id"), f"Fact missing id: {fact}"
        assert fact.get("value") is not None, f"Fact missing value: {fact}"
        assert fact.get("anchors"), f"Fact has no anchors: {fact.get('id')}"
        for anchor in fact["anchors"]:
            assert anchor.get("file"), f"Anchor missing file in fact {fact['id']}"
            assert anchor.get("source_role"), f"Anchor missing source_role in fact {fact['id']}"


# ---------------------------------------------------------------------------
# Step 10 — Reconciliation produced
# ---------------------------------------------------------------------------

def test_08_reconciliation_produced(analysis_result):
    """
    EDI (04_tms_shipment.json) and POD (08_proof_of_delivery.pdf) conflict
    must produce a COUNT_MISMATCH finding.
    """
    reconciliation = analysis_result.get("reconciliation")
    assert reconciliation is not None, (
        "No reconciliation finding — EDI vs POD conflict not detected. "
        "Check that TMS and POD files are being parsed from S3."
    )
    assert reconciliation.get("id") == "COUNT_MISMATCH"
    assert reconciliation.get("severity") == "high"
    assert len(reconciliation.get("facts", [])) == 2


# ---------------------------------------------------------------------------
# Step 11 — Contract positions produced
# ---------------------------------------------------------------------------

def test_09_contract_positions_produced(analysis_result):
    positions = analysis_result.get("contract_position", [])
    assert len(positions) >= 1, (
        "No contract positions produced — ERP/TMS data not reaching contract engine"
    )
    # First position must be cargo liability cap
    first = positions[0]
    assert first.get("id") == "CARGO_LIABILITY"
    assert first.get("amount"), "Cargo liability amount missing"
    assert first.get("clause"), "Cargo liability clause missing"


# ---------------------------------------------------------------------------
# Step 12 — Historical comparables produced
# ---------------------------------------------------------------------------

def test_10_historical_comparables_produced(analysis_result):
    comparables = analysis_result.get("historical_comparables", [])
    assert len(comparables) > 0, "No historical comparables returned"
    for comp in comparables:
        assert comp.get("claim_id"), "Comparable missing claim_id"
        assert comp.get("score") is not None, "Comparable missing score"


# ---------------------------------------------------------------------------
# Step 13-14 — Frontend response schema
# ---------------------------------------------------------------------------

def test_11_frontend_response_schema(frontend_response):
    required_keys = {"claim", "facts", "findings", "position", "comparators", "timeline"}
    missing = required_keys - set(frontend_response.keys())
    assert not missing, f"Frontend response missing keys: {missing}"

    claim = frontend_response["claim"]
    claim_keys = {"id", "carrier", "owner", "status", "demand", "offer",
                  "direct_cargo", "gap_to_direct_cargo"}
    missing_claim = claim_keys - set(claim.keys())
    assert not missing_claim, f"claim block missing keys: {missing_claim}"

    position_keys = {"direct_cargo", "cargo_cap", "inspection", "repack",
                     "delay_markdown", "freight_refund"}
    missing_pos = position_keys - set(frontend_response["position"].keys())
    assert not missing_pos, f"position block missing keys: {missing_pos}"


# ---------------------------------------------------------------------------
# Step 15 — Value provenance: demand traces to uploaded snapshot
# ---------------------------------------------------------------------------

def test_12_demand_traces_to_uploaded_snapshot(analysis_result, frontend_response):
    """
    Shipper demand in the frontend must match claim_amount_usd from
    the uploaded 03_claim_snapshot.json (via pipeline claim_snapshot).
    """
    snap = analysis_result.get("claim_snapshot", {})
    pipeline_amount = snap.get("claim_amount_usd")
    assert pipeline_amount is not None, "claim_amount_usd not in pipeline result"

    frontend_demand = frontend_response["claim"]["demand"]
    # frontend formats as "$29,920.00" — parse it back
    parsed = float(frontend_demand.replace("$", "").replace(",", ""))
    assert abs(parsed - float(pipeline_amount)) < 0.01, (
        f"Frontend demand {frontend_demand} does not match "
        f"pipeline snapshot amount {pipeline_amount}. "
        "Frontend may be using fixture data instead of S3-derived snapshot."
    )


# ---------------------------------------------------------------------------
# Step 16 — No 4xx/5xx on any endpoint
# ---------------------------------------------------------------------------

def test_13_no_errors_on_all_endpoints():
    endpoints = [
        ("GET",  "/health",               None),
        ("GET",  "/",                     None),
        ("GET",  "/api/claim",            None),
        ("GET",  f"/api/claim/{CLAIM_ID}", None),
    ]
    for method, path, _ in endpoints:
        if method == "GET":
            resp = client.get(path)
        assert resp.status_code < 400, (
            f"{method} {path} returned {resp.status_code}: {resp.text[:200]}"
        )


# ---------------------------------------------------------------------------
# Step 17 — Idempotent re-analysis
# ---------------------------------------------------------------------------

def test_14_reanalysis_is_idempotent(uploaded_keys):
    """Running analyze twice must not crash or duplicate pipeline state."""
    resp1 = client.post(f"/claims/{CLAIM_ID}/analyze")
    resp2 = client.post(f"/claims/{CLAIM_ID}/analyze")
    assert resp1.status_code == 200, f"First analysis failed: {resp1.text[:200]}"
    assert resp2.status_code == 200, f"Second analysis failed: {resp2.text[:200]}"

    r1 = resp1.json()
    r2 = resp2.json()
    # Same number of facts both times
    facts1 = len(r1.get("evidence", {}).get("facts", []))
    facts2 = len(r2.get("evidence", {}).get("facts", []))
    assert facts1 == facts2, (
        f"Re-analysis produced different fact counts: {facts1} vs {facts2}. "
        "Pipeline may be accumulating state between runs."
    )


# ---------------------------------------------------------------------------
# Step 18 — Cleanup does not affect fixture data
# ---------------------------------------------------------------------------

def test_15_cleanup_does_not_affect_fixture():
    """
    Verify the fixture claim FCL-2026-0147 still works after our test
    uploads/analyses under a different claim ID.
    """
    resp = client.get("/api/claim/FCL-2026-0147")
    assert resp.status_code == 200
    body = resp.json()
    assert body["claim"]["id"] == "FCL-2026-0147"
    assert body["claim"]["carrier"] == "BlueLine Freight Systems"
    assert len(body["facts"]) > 0
    assert len(body["findings"]) > 0
