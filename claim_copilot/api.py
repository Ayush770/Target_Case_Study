from __future__ import annotations

import os
import tempfile
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import build_case, build_draft
from claim_processor import process_claim
from genai_service import generate_draft as genai_generate_draft
from s3_service import S3Service

# ---------------------------------------------------------------------------
# Paths — always resolved relative to this file so the app works regardless
# of the working directory uvicorn is launched from.
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE / "static"


# =====================================================
# Application
# =====================================================

app = FastAPI(
    title="Freight Claim Copilot",
    version="1.0",
)


# =====================================================
# Static Frontend
# =====================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


# =====================================================
# Health
# =====================================================

@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "Freight Claim Copilot",
    }


# =====================================================
# Serialization
#
# Handles nested dataclasses, lists, dicts, and
# Decimal values (which are not JSON-serializable
# by default and would crash FastAPI's encoder).
# =====================================================

def serialize_response(obj: Any) -> Any:
    if obj is None:
        return None

    if isinstance(obj, Decimal):
        # Preserve precision as a string so the client gets "0.750"
        # rather than a lossy float.
        return str(obj)

    if is_dataclass(obj) and not isinstance(obj, type):
        return {
            key: serialize_response(value)
            for key, value in asdict(obj).items()
        }

    if isinstance(obj, list):
        return [serialize_response(item) for item in obj]

    if isinstance(obj, dict):
        return {key: serialize_response(value) for key, value in obj.items()}

    return obj


# =====================================================
# S3 service factory
#
# A new client is created per-request so that credential
# refreshes (e.g. re-running `aws login` or setting env
# vars) take effect without restarting the server.
# =====================================================

def get_s3_service() -> S3Service:
    return S3Service()


# =====================================================
# Document Upload
# =====================================================

@app.post("/claims/{claim_id}/documents")
async def upload_document(
    claim_id: str,
    file: UploadFile = File(...),
) -> dict[str, str]:
    suffix = os.path.splitext(file.filename or "")[1]

    # Write upload to a temp file so boto3 can read it from disk.
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        s3_key = get_s3_service().upload_file(
            file_path=tmp_path,
            claim_id=claim_id,
            filename=file.filename or "uploaded_file",
        )
    except Exception as exc:
        # Surface the real AWS error so the frontend shows an actionable
        # message rather than a generic "Failed".
        err_msg = str(exc)
        # Make the most common error (expired session) easy to understand
        if "reauthenticate" in err_msg or "login session" in err_msg.lower():
            err_msg = (
                "AWS credentials are expired or missing. "
                "Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION "
                "environment variables, then restart the server. "
                f"Original error: {exc}"
            )
        raise HTTPException(status_code=502, detail=err_msg)
    finally:
        os.unlink(tmp_path)

    return {
        "claim_id": claim_id,
        "filename": file.filename or "uploaded_file",
        "s3_key":   s3_key,
        "status":   "uploaded",
    }


# =====================================================
# Claim Analysis — raw pipeline output
# =====================================================

@app.post("/claims/{claim_id}/analyze")
def analyze_claim(claim_id: str) -> Any:
    try:
        result = process_claim(claim_id)
        serialized = serialize_response(result)
        # Include claim_id explicitly so the frontend can route to
        # GET /api/claim/{claim_id} after analysis completes.
        serialized["claim_id"] = claim_id
        return serialized
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# =====================================================
# Frontend Adapter
#
# Converts the process_claim result into the shape
# that app.js expects. All values come from the
# pipeline — nothing is hardcoded here.
# =====================================================

def _map_contract_position(pos: dict[str, Any]) -> dict[str, Any]:
    """Normalise a serialized ContractPosition dict to the frontend shape."""
    return {
        "amount": pos.get("amount", "$0.00"),
        "status": pos.get("status", ""),
        "clause": pos.get("clause", ""),
        # rationale is extra context; expose it so the UI can show it
        "rationale": pos.get("rationale", ""),
    }


def build_frontend_claim_response(claim_id: str) -> dict[str, Any]:
    # ------------------------------------------------------------------
    # Run the live pipeline first.  For the demo fixture claim this is
    # supplemented by build_case() (which has richer formulas/timeline).
    # For any other claim_id the pipeline result IS the response — we do
    # not fall back to the fixture data.
    # ------------------------------------------------------------------
    IS_FIXTURE = claim_id in ("CLAIM-001", "FCL-2026-0147")

    try:
        pipeline      = process_claim(claim_id)
        pipeline_data = serialize_response(pipeline)
        pipeline_ok   = True
    except Exception:
        pipeline_data = {}
        pipeline_ok   = False

    # Only load the fixture case when we're serving the demo claim
    if IS_FIXTURE:
        try:
            case = build_case()
        except Exception:
            case = {}
    else:
        case = {}

    # ------------------------------------------------------------------
    # Facts — prefer pipeline; fall back to fixture for demo claim only
    # ------------------------------------------------------------------
    pipeline_facts = pipeline_data.get("evidence", {}).get("facts", []) if pipeline_ok else []
    facts = pipeline_facts or case.get("facts", [])

    # ------------------------------------------------------------------
    # Findings — live reconciliation first, then fixture findings
    # ------------------------------------------------------------------
    live_findings: list[dict[str, Any]] = []
    if pipeline_ok and pipeline_data.get("reconciliation"):
        live_findings = [pipeline_data["reconciliation"]]
    live_ids = {f["id"] for f in live_findings}
    fixture_findings = case.get("findings", []) if IS_FIXTURE else []
    merged_findings  = live_findings + [f for f in fixture_findings if f["id"] not in live_ids]

    # ------------------------------------------------------------------
    # Contract positions — pipeline when present, fixture as fallback
    # ------------------------------------------------------------------
    pipeline_positions = pipeline_data.get("contract_position", []) if pipeline_ok else []

    def _pos(index: int) -> dict[str, Any]:
        if pipeline_positions and len(pipeline_positions) > index:
            return _map_contract_position(pipeline_positions[index])
        return {}

    fixture_pos = case.get("position", {})

    position = {
        "direct_cargo":   _pos(0) or fixture_pos.get("direct_cargo", {}),
        "cargo_cap":      _pos(0) or fixture_pos.get("cargo_cap", {}),
        "inspection":     _pos(1) or fixture_pos.get("inspection", {}),
        "repack":         _pos(2) or fixture_pos.get("repack", {}),
        "delay_markdown": _pos(3) or fixture_pos.get("delay_markdown", {}),
        "freight_refund": fixture_pos.get("freight_refund", {}),
    }
    # For the fixture claim, direct_cargo is separate from cargo_cap
    if IS_FIXTURE and fixture_pos.get("direct_cargo"):
        position["direct_cargo"] = fixture_pos["direct_cargo"]

    # ------------------------------------------------------------------
    # Comparators
    # ------------------------------------------------------------------
    comparators = (
        pipeline_data.get("historical_comparables", [])
        if pipeline_ok
        else case.get("comparators", [])
    )

    # ------------------------------------------------------------------
    # Claim header block
    # Use pipeline snapshot when available (reflects uploaded files).
    # Fall back to build_case() for the fixture claim when pipeline
    # did not produce a snapshot (e.g. pipeline failed entirely).
    # ------------------------------------------------------------------
    pipeline_snapshot = pipeline_data.get("claim_snapshot", {}) if pipeline_ok else {}

    if pipeline_snapshot:
        # Pipeline ran and returned snapshot data — use it directly.
        # build_case() provides the carrier offer (parsed from email)
        # and the direct_cargo calculation; merge them.
        fixture_claim = case.get("claim", {})
        claim_block = {
            "id":                  pipeline_snapshot.get("claim_id", claim_id),
            "carrier":             pipeline_snapshot.get("carrier", fixture_claim.get("carrier", "—")),
            "owner":               pipeline_snapshot.get("owner", fixture_claim.get("owner", "—")),
            "status":              pipeline_snapshot.get("status", fixture_claim.get("status", "ANALYZED")),
            "demand":              f"${float(pipeline_snapshot.get('claim_amount_usd', 0)):,.2f}",
            # offer comes from build_case() (parsed from email) — keep it when available
            "offer":               fixture_claim.get("offer", "—"),
            # direct_cargo and gap come from build_case() calculation when fixture,
            # or remain as computed by the pipeline position
            "direct_cargo":        fixture_claim.get("direct_cargo", "—"),
            "gap_to_direct_cargo": fixture_claim.get("gap_to_direct_cargo", "—"),
        }
    else:
        claim_block = case.get("claim", {
            "id":                claim_id,
            "carrier":           "—",
            "owner":             "—",
            "status":            "ANALYZED",
            "demand":            "—",
            "offer":             "—",
            "direct_cargo":      "—",
            "gap_to_direct_cargo": "—",
        })

    return {
        "claim":       claim_block,
        "facts":       facts,
        "findings":    merged_findings,
        "position":    position,
        "comparators": comparators,
        "timeline":    case.get("timeline", []),
    }


# =====================================================
# Frontend GET APIs
# =====================================================

@app.get("/api/claim")
def get_default_claim() -> Any:
    try:
        return build_frontend_claim_response("CLAIM-001")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/claim/{claim_id}")
def get_claim_by_id(claim_id: str) -> Any:
    try:
        return build_frontend_claim_response(claim_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# =====================================================
# Evidence file serving
#
# Mirrors the /evidence/<filename> route from app.py's
# SimpleHTTPRequestHandler so the frontend source links
# work when running under uvicorn.
# =====================================================

ROOT = HERE.parent


@app.get("/evidence/{filename}")
def serve_evidence(filename: str) -> FileResponse:
    candidate = ROOT / filename
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Evidence file not found")
    # Restrict to the project root — no path traversal
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    return FileResponse(str(candidate))


# =====================================================
# Negotiation Draft
# =====================================================

@app.post("/api/draft")
def generate_draft() -> Any:
    try:
        case = build_case()
        deterministic = build_draft(case)
        return genai_generate_draft(case, deterministic)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
