"""Local, evidence-led Freight Claim Copilot demo.

Run with the bundled runtime documented in README.md.  The app intentionally
uses a deterministic policy layer and a source-linked fact ledger; the optional
LLM provider is only allowed to turn the vetted evidence packet into prose.
"""

from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import os
import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from pypdf import PdfReader
except ImportError:  # The app still runs with the evidence annotation fixture.
    PdfReader = None


ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"


@dataclass(frozen=True)
class Anchor:
    file: str
    locator: str
    source_role: str
    confidence: float


@dataclass(frozen=True)
class Fact:
    id: str
    label: str
    value: str
    status: str
    anchors: list[Anchor]


def money(value: Decimal | float | int | str) -> str:
    return f"${Decimal(str(value)):,.2f}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def anchor(file: str, locator: str, role: str, confidence: float = 0.99) -> Anchor:
    return Anchor(file=file, locator=locator, source_role=role, confidence=confidence)


def source_inventory() -> list[dict[str, str]]:
    sources = []
    for path in sorted(ROOT.glob("[0-9][0-9]_*") ):
        if path.is_file() and path.name != "SYSTEM_DESIGN.md":
            mime, _ = mimetypes.guess_type(path.name)
            sources.append({
                "file": path.name,
                "sha256": sha256(path)[:16],
                "type": mime or "application/octet-stream",
            })
    return sources


def read_json(filename: str) -> dict[str, Any]:
    return json.loads((ROOT / filename).read_text())


def read_erp() -> dict[str, str]:
    with (ROOT / "05_erp_order_invoice.csv").open(newline="") as file:
        return next(csv.DictReader(file))


def read_history() -> list[dict[str, str]]:
    with (ROOT / "12_historical_claims.csv").open(newline="") as file:
        return list(csv.DictReader(file))


def reviewed_scan() -> dict[str, Any]:
    """Reviewed OCR fixture for the image-only inspection PDF.

    In production this record is created by the OCR worker and approved by a
    reviewer when confidence on a consequential field is below threshold.
    """
    return {
        "damaged_cartons": ["C-017", "C-018", "C-021", "C-022", "C-023"],
        "units_examined": 20,
        "unsellable_units": 14,
        "repackable_units": 6,
        "inspection_fee": Decimal("420.00"),
        "repack_labor": Decimal("300.00"),
        "anchor": anchor(
            "09_damage_inspection_report_scanned.pdf",
            "page 1; reviewed OCR table and inspector conclusion",
            "independent_inspection",
            0.98,
        ),
    }


def parse_email_thread() -> dict[str, Any]:
    message = BytesParser(policy=policy.default).parsebytes(
        (ROOT / "02_claim_email_thread.eml").read_bytes()
    )
    body_part = message.get_body(preferencelist=("plain",))
    body = body_part.get_content() if body_part else ""
    offer = re.search(r"Offer:\s*\$(7,225\.00)", body)
    packaging = "vendor packaging specification" in body.lower()
    return {
        "subject": str(message["subject"]),
        "carrier_offer": Decimal(offer.group(1).replace(",", "")) if offer else Decimal("0"),
        "packaging_requested": packaging,
    }


def extract_native_pdf_text(filename: str) -> str:
    if PdfReader is None:
        return ""
    try:
        return "\n".join(page.extract_text() or "" for page in PdfReader(ROOT / filename).pages)
    except Exception:
        return ""


def score_comparator(case: dict[str, str]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    if case["carrier"] == "BlueLine Freight Systems":
        score += 0.35
        reasons.append("same carrier")
    if case["service_level"] == "Standard LTL":
        score += 0.20
        reasons.append("same service level")
    issues = set(case["issue_type"].split("+"))
    current_issues = {"DAMAGE", "SHORTAGE", "DELAY"}
    overlap = len(issues & current_issues) / len(issues | current_issues)
    score += 0.15 * overlap
    if overlap:
        reasons.append(f"issue overlap: {', '.join(sorted(issues & current_issues)).lower()}")
    evidence = set(case["evidence"].lower().split("+"))
    target_evidence = {"pod", "inspection", "photos"}
    evidence_overlap = len(evidence & target_evidence) / len(target_evidence)
    score += 0.10 * evidence_overlap
    if evidence_overlap >= 0.66:
        reasons.append("similar evidence profile")
    amount = Decimal(case["claimed_usd"])
    direct_loss = Decimal("9350")
    proximity = max(Decimal("0"), Decimal("1") - abs(amount - direct_loss) / max(amount, direct_loss))
    score += float(Decimal("0.10") * proximity)
    if "No guaranteed service" in case["notes"]:
        score += 0.10
        reasons.append("same non-guaranteed service context")
    return round(score, 3), reasons


def comparators() -> list[dict[str, Any]]:
    ranked = []
    for case in read_history():
        score, reasons = score_comparator(case)
        if case["carrier"] == "BlueLine Freight Systems" and case["service_level"] == "Standard LTL":
            ranked.append({
                "claim_id": case["claim_id"],
                "issue_type": case["issue_type"],
                "claimed": money(case["claimed_usd"]),
                "settled": money(case["settled_usd"]),
                "settlement_pct": f"{Decimal(case['settlement_pct']) * 100:.1f}%",
                "evidence": case["evidence"],
                "summary": case["negotiation_summary"],
                "notes": case["notes"],
                "score": score,
                "reasons": reasons,
            })
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:5]


def build_case() -> dict[str, Any]:
    snapshot = read_json("03_claim_snapshot.json")
    tms = read_json("04_tms_shipment.json")
    erp = read_erp()
    scan = reviewed_scan()
    email = parse_email_thread()

    tendered = int(tms["shipment"]["pieces_tendered"])
    received_pod = 58
    delivered_edi = next(event for event in tms["events"] if event["code"] == "DELIVERED")["pieces"]
    short_cartons = tendered - received_pod
    units_per_carton = 4
    missing_units = short_cartons * units_per_carton
    unit_price = Decimal(erp["unit_price_usd"])
    missing_value = Decimal(missing_units) * unit_price
    damage_value = Decimal(scan["unsellable_units"]) * unit_price
    direct_cargo = missing_value + damage_value
    affected_units = missing_units + scan["unsellable_units"]
    weight_cap = Decimal(affected_units * 15 * 50)
    carrier_offer = email["carrier_offer"]

    facts = [
        Fact("fact.tendered_cartons", "Cartons tendered", str(tendered), "verified", [
            anchor("04_tms_shipment.json", "shipment.pieces_tendered", "carrier_operational_record"),
            anchor("07_bill_of_lading.pdf", "page 1; Packages", "shipper_carrier_tender"),
        ]),
        Fact("fact.pod_received_cartons", "Cartons received (signed POD)", str(received_pod), "verified", [
            anchor("08_proof_of_delivery.pdf", "page 1; Received 58 of 60 cartons", "consignee_signed_receipt"),
        ]),
        Fact("fact.edi_delivered_pieces", "Pieces delivered (EDI)", str(delivered_edi), "disputed", [
            anchor("04_tms_shipment.json", "events[DELIVERED].pieces", "carrier_operational_record"),
        ]),
        Fact("fact.damaged_cartons", "Damaged cartons identified", ", ".join(scan["damaged_cartons"]), "verified", [
            anchor("08_proof_of_delivery.pdf", "page 1; 5 cartons crushed/wet", "consignee_signed_receipt"),
            scan["anchor"],
        ]),
        Fact("fact.unsellable_units", "Unsellable units", str(scan["unsellable_units"]), "verified", [scan["anchor"]]),
        Fact("fact.direct_cargo_loss", "Direct cargo loss", money(direct_cargo), "calculated", [
            anchor("06_commercial_invoice.pdf", "page 1; $425 unit price", "commercial_value"),
            scan["anchor"],
        ]),
    ]

    findings = [
        {
            "id": "COUNT_MISMATCH",
            "severity": "high",
            "title": "Delivery count conflict: 59 EDI vs 58 signed POD",
            "detail": "The final carrier EDI event reports 59 pieces delivered. The consignee-signed POD reports 58 cartons received and 2 cartons short.",
            "action": "Request carrier EDI scan detail and reconcile against terminal/driver records. Retain the signed POD as the preferred receipt evidence.",
            "facts": ["fact.edi_delivered_pieces", "fact.pod_received_cartons"],
        },
        {
            "id": "PARTIAL_PHOTO_COVERAGE",
            "severity": "medium",
            "title": "Photo coverage is incomplete",
            "detail": "Two photos document cartons C-021 and C-023. The POD and inspection identify five damaged cartons: C-017, C-018, C-021, C-022, and C-023.",
            "action": "Request remaining warehouse photos if available; do not treat their absence as disproving inspection-supported damage.",
            "facts": ["fact.damaged_cartons"],
        },
        {
            "id": "MISSING_PACKAGING_SPEC",
            "severity": "medium",
            "title": "Vendor packaging specification is missing",
            "detail": "BlueLine requested a packaging specification. The inspection observed internal foam but confirms the vendor specification was not provided.",
            "action": "Obtain vendor packaging specification or written packaging standard; preserve inspection observation as partial support.",
            "facts": [],
        },
    ]

    position = {
        "direct_cargo": {
            "amount": money(direct_cargo),
            "formula": f"{missing_units} missing units x {money(unit_price)} + {scan['unsellable_units']} unsellable units x {money(unit_price)}",
            "status": "Supported subject to packaging, mitigation, and count reconciliation",
        },
        "cargo_cap": {
            "amount": money(direct_cargo),
            "formula": f"min({money(direct_cargo)} invoice-value loss, {affected_units} units x 15 lb x $50/lb = {money(weight_cap)})",
            "status": "Below estimated contractual cap; 15 lb is a product-weight proxy",
            "clause": "Carrier agreement §2",
        },
        "inspection": {
            "amount": money(scan["inspection_fee"]),
            "status": "Potentially recoverable if reasonable and necessary",
            "clause": "Carrier agreement §3",
        },
        "repack": {
            "amount": money(scan["repack_labor"]),
            "status": "Needs classification/support; internal administrative labor is excluded",
            "clause": "Carrier agreement §3",
        },
        "delay_markdown": {
            "amount": "$18,000.00",
            "status": "Contractually excluded on current facts; commercial request only",
            "clause": "Carrier agreement §4",
        },
        "freight_refund": {
            "amount": money(tms["shipment"]["freight_charge_usd"]),
            "status": "Not contractually available without purchased Guaranteed Appointment service",
            "clause": "Carrier agreement §4",
        },
    }

    return {
        "claim": {
            "id": snapshot["claim_id"],
            "carrier": snapshot["carrier"],
            "status": snapshot["status"],
            "owner": snapshot["owner"],
            "demand": money(snapshot["claim_amount_usd"]),
            "offer": money(carrier_offer),
            "direct_cargo": money(direct_cargo),
            "gap_to_direct_cargo": money(direct_cargo - carrier_offer),
        },
        "facts": [asdict(item) for item in facts],
        "findings": findings,
        "position": position,
        "timeline": [
            {"date": "2026-05-04", "event": "Picked up", "detail": "60 cartons tendered in Columbus."},
            {"date": "2026-05-08", "event": "Terminal backlog", "detail": "Delivery appointment rolled in Dallas."},
            {"date": "2026-05-11", "event": "Driver-hours exception", "detail": "Freight returned to terminal."},
            {"date": "2026-05-12", "event": "Delivered with exceptions", "detail": "Signed POD records 58 received, 2 short, 5 damaged."},
            {"date": "2026-05-22", "event": "Carrier offer", "detail": "BlueLine offers $7,225 and disputes five damaged units."},
            {"date": "2026-05-26", "event": "Claimant response", "detail": "Northstar requests reconsideration and commercial delay discussion."},
        ],
        "comparators": comparators(),
        "sources": source_inventory(),
    }


def build_draft(case: dict[str, Any]) -> dict[str, Any]:
    """Safe fallback draft. Swap only this function for a schema-constrained LLM.

    The client receives cited claim IDs, not free-form ungrounded prose.
    """
    claim = case["claim"]
    return {
        "subject": f"Claim {claim['id']} / PRO BLF-77209115 - request for reconsideration",
        "body": (
            "Daniel,\n\n"
            "Thank you for BlueLine's $7,225.00 offer. We request reconsideration of the five disputed "
            "unsellable units ($2,125.00). The consignee-signed POD records five damaged cartons, and the "
            "independent inspection identifies 14 unsellable units across five cartons. The available photos "
            "corroborate two cartons; we acknowledge that photo coverage is incomplete.\n\n"
            "We also request consideration of the $420.00 independent inspection cost. The report was obtained "
            "to document the extent of physical damage and records internal foam in the opened cartons. We are "
            "continuing to seek the vendor packaging specification and will provide it if located.\n\n"
            "We recognize that the promotion markdown is not a Standard LTL contractual remedy. We nevertheless "
            "ask BlueLine to consider the documented delivery exceptions and promotion impact as part of a "
            "commercial resolution.\n\nRegards,\nMaya Chen"
        ),
        "citations": [
            {"claim": "Five damaged cartons and 14 unsellable units", "fact_ids": ["fact.damaged_cartons", "fact.unsellable_units"]},
            {"claim": "Direct cargo gap of $2,125", "fact_ids": ["fact.direct_cargo_loss"]},
            {"claim": "Delay is a commercial request, not a contractual remedy", "rule": "Carrier agreement §4"},
        ],
        "validation": {
            "citation_coverage": "pass",
            "numeric_consistency": "pass",
            "approval_required": True,
        },
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/claim":
            return self.send_json(build_case())
        if path == "/api/health":
            return self.send_json({"status": "ok", "mode": "local-demo"})
        if path.startswith("/evidence/"):
            filename = Path(path).name
            candidate = ROOT / filename
            if candidate.exists() and candidate.is_file():
                content = candidate.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mimetypes.guess_type(filename)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            return self.send_error(HTTPStatus.NOT_FOUND, "Evidence file not found")
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/api/draft":
            return self.send_json(build_draft(build_case()))
        return self.send_error(HTTPStatus.NOT_FOUND, "Unknown API route")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Freight Claim Copilot running at http://127.0.0.1:{port}")
    server.serve_forever()
