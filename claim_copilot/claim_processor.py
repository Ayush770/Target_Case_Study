from pathlib import Path
import json
import csv
from decimal import Decimal

from document_extractor import extract_pdf_text

from claim_evidence import ClaimEvidence

from pod_parser import parse_pod
from textract_evidence_adapter import parse_inspection_report
from tms_evidence_adapter import parse_tms_delivery_fact

from textract_service import TextractService

from reconciliation import reconcile_delivery_counts

from contract_engine import (
    cargo_liability_cap,
    inspection_cost_position,
    repack_labor_position,
    delay_position,
)

from historical_comparator import find_comparables


from pathlib import Path
import json
import csv
import tempfile
import os
from decimal import Decimal

from document_extractor import extract_pdf_text

from claim_evidence import ClaimEvidence

from pod_parser import parse_pod
from textract_evidence_adapter import parse_inspection_report
from tms_evidence_adapter import parse_tms_delivery_fact

from textract_service import TextractService

from reconciliation import reconcile_delivery_counts

from contract_engine import (
    cargo_liability_cap,
    inspection_cost_position,
    repack_labor_position,
    delay_position,
)

from historical_comparator import find_comparables


ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Document-type registry
#
# Maps the canonical fixture filename to the parser that handles it.
# When a user uploads a document under any of these names (or a name
# containing the key substring), the uploaded file is used in place of the
# fixture.  Any uploaded file not recognised here is silently skipped
# rather than causing a crash.
# ---------------------------------------------------------------------------

# Key   = lowercase substring to match in the uploaded filename
# Value = role label used to route the file to the right parser
_FILENAME_ROLE_MAP = {
    "proof_of_delivery": "pod",
    "08_proof":          "pod",
    "bill_of_lading":    "bol",
    "07_bill":           "bol",
    "inspection":        "inspection",
    "09_damage":         "inspection",
    "tms":               "tms",
    "04_tms":            "tms",
    "shipment":          "tms",
    "erp":               "erp",
    "05_erp":            "erp",
    "invoice":           "erp",
    "claim_snapshot":    "snapshot",
    "03_claim":          "snapshot",
}


def _detect_role(filename: str) -> str | None:
    """Return the evidence role for a filename, or None if unrecognised."""
    name = filename.lower()
    for substring, role in _FILENAME_ROLE_MAP.items():
        if substring in name:
            return role
    return None


def _try_s3_documents(claim_id: str) -> dict[str, Path]:
    """
    Attempt to list and download uploaded documents from S3 for this claim.
    Returns a dict mapping role -> local temp path.
    Returns an empty dict if S3 is unavailable or no documents are uploaded.
    """
    try:
        from s3_service import S3Service
        svc  = S3Service()
        keys = svc.list_claim_documents(claim_id)
    except Exception:
        return {}

    if not keys:
        return {}

    role_to_path: dict[str, Path] = {}

    for key in keys:
        filename = key.split("/")[-1]
        role     = _detect_role(filename)
        if role is None or role in role_to_path:
            # Unknown type or already have a file for this role — skip
            continue

        suffix = os.path.splitext(filename)[1] or ".tmp"
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.close()
            svc.download_file(key, tmp.name)
            role_to_path[role] = Path(tmp.name)
        except Exception:
            # Download failed — fall back to fixture for this role
            pass

    return role_to_path


def load_json(filename: str):
    with open(ROOT / filename, "r") as file:
        return json.load(file)


def load_csv(filename: str):
    with open(ROOT / filename, newline="") as file:
        return list(csv.DictReader(file))


def build_claim_evidence(claim_id: str) -> ClaimEvidence:

    evidence = ClaimEvidence(
        claim_id=claim_id
    )

    # ------------------------------------------------------------------
    # Attempt to use documents uploaded to S3 for this claim.
    # Falls back silently to fixture files for any role not uploaded.
    # ------------------------------------------------------------------
    uploaded = _try_s3_documents(claim_id)
    _temp_paths = list(uploaded.values())   # collected for cleanup

    try:
        # ---------------------------------
        # POD Evidence
        # Digital PDF -> pypdf extractor
        # ---------------------------------

        pod_path = uploaded.get("pod", ROOT / "08_proof_of_delivery.pdf")

        pod_text = extract_pdf_text(pod_path)

        pod_facts = parse_pod(pod_text)

        evidence.add_facts(pod_facts)


        # ---------------------------------
        # Inspection Evidence
        # Scanned PDF -> AWS Textract (with graceful fallback)
        # ---------------------------------

        inspection_path = uploaded.get(
            "inspection",
            ROOT / "09_damage_inspection_report_scanned.pdf",
        )

        try:
            textract = TextractService()
            inspection_text = textract.extract_text(str(inspection_path))
        except Exception:
            # No AWS credentials or Textract unavailable — try pypdf
            # for native PDFs; scanned-only PDFs will yield empty text.
            inspection_text = extract_pdf_text(inspection_path)

        inspection_facts = parse_inspection_report(inspection_text)

        evidence.add_facts(inspection_facts)


        # ---------------------------------
        # TMS / EDI Evidence
        # JSON -> EvidenceFact
        # ---------------------------------

        tms_path = uploaded.get("tms")
        if tms_path:
            with open(tms_path, "r") as f:
                tms_data = json.load(f)
        else:
            tms_data = load_json("04_tms_shipment.json")

        tms_facts = parse_tms_delivery_fact(tms_data)

        evidence.add_facts(tms_facts)

    finally:
        # Clean up all temporary files downloaded from S3
        for p in _temp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    return evidence



def process_claim(claim_id: str):

    # ------------------------------------------------------------------
    # Check for uploaded source documents for this claim.
    # Structured files (JSON/CSV) are read directly from the temp path.
    # Falls back to fixture files for any role not uploaded.
    # ------------------------------------------------------------------
    uploaded = _try_s3_documents(claim_id)
    _temp_paths = list(uploaded.values())

    try:
        # ---------------------------------
        # Load source systems
        # ---------------------------------

        if "tms" in uploaded:
            with open(uploaded["tms"], "r") as f:
                tms = json.load(f)
        else:
            tms = load_json("04_tms_shipment.json")

        if "snapshot" in uploaded:
            with open(uploaded["snapshot"], "r") as f:
                claim_snapshot = json.load(f)
        else:
            claim_snapshot = load_json("03_claim_snapshot.json")

        if "erp" in uploaded:
            with open(uploaded["erp"], newline="") as f:
                erp_invoice = next(csv.DictReader(f))
        else:
            erp_invoice = load_csv("05_erp_order_invoice.csv")[0]

        historical_claims = load_csv("12_historical_claims.csv")

        # ---------------------------------
        # Evidence aggregation
        # ---------------------------------

        evidence = build_claim_evidence(claim_id)

        # ---------------------------------
        # Reconciliation
        # ---------------------------------

        edi_fact = evidence.get_fact("fact.edi_delivered_pieces")
        pod_fact = evidence.get_fact("fact.pod_received_cartons")

        reconciliation = None

        if edi_fact and pod_fact:
            reconciliation = reconcile_delivery_counts(edi_fact, pod_fact)

        # ---------------------------------
        # Contract Evaluation
        # ---------------------------------

        contract_positions = []

        invoice_value  = erp_invoice.get("extended_value_usd")
        shipment_weight = tms.get("shipment", {}).get("weight_lb")

        if invoice_value and shipment_weight:
            contract_positions.append(
                cargo_liability_cap(
                    invoice_value=Decimal(invoice_value),
                    affected_weight_lbs=Decimal(str(shipment_weight)),
                )
            )

        inspection_fact = evidence.get_fact("fact.inspection_cost")
        if inspection_fact:
            contract_positions.append(
                inspection_cost_position(
                    inspection_cost=Decimal(inspection_fact.value)
                )
            )

        repack_fact = evidence.get_fact("fact.repack_labor")
        if repack_fact:
            contract_positions.append(
                repack_labor_position(
                    repack_cost=Decimal(repack_fact.value)
                )
            )

        claim_amount = claim_snapshot.get("claim_amount_usd")
        if claim_amount:
            contract_positions.append(
                delay_position(
                    requested_amount=Decimal(str(claim_amount)),
                    guaranteed_service=(
                        tms.get("service", {}).get("guaranteed")
                    ),
                )
            )

        # ---------------------------------
        # Historical Comparator
        # ---------------------------------

        current_claim = {
            "carrier":       claim_snapshot.get("carrier"),
            "service_level": tms.get("service", {}).get("name"),
            "issue_type":    " ".join(
                claim_snapshot.get("claim_type_codes", [])
            ),
            "claimed_usd":   str(claim_snapshot.get("claim_amount_usd")),
            "evidence":      " ".join(evidence.source_files()),
        }

        comparables = find_comparables(current_claim, historical_claims)

    finally:
        for p in _temp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    return {
        "claim_id":              claim_id,
        "claim_snapshot":        claim_snapshot,
        "evidence":              evidence,
        "reconciliation":        reconciliation,
        "contract_position":     contract_positions,
        "historical_comparables": comparables,
    }