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


ROOT = Path("..")


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


    # ---------------------------------
    # POD Evidence
    # Digital PDF -> pypdf extractor
    # ---------------------------------

    pod_text = extract_pdf_text(
        ROOT / "08_proof_of_delivery.pdf"
    )

    pod_facts = parse_pod(
        pod_text
    )

    evidence.add_facts(
        pod_facts
    )


    # ---------------------------------
    # Inspection Evidence
    # Scanned PDF -> AWS Textract
    # ---------------------------------

    textract = TextractService()

    inspection_text = textract.extract_text(
        str(
            ROOT / "09_damage_inspection_report_scanned.pdf"
        )
    )

    inspection_facts = parse_inspection_report(
        inspection_text
    )

    evidence.add_facts(
        inspection_facts
    )


    # ---------------------------------
    # TMS / EDI Evidence
    # JSON -> EvidenceFact
    # ---------------------------------

    tms_data = load_json(
        "04_tms_shipment.json"
    )

    tms_facts = parse_tms_delivery_fact(
        tms_data
    )

    evidence.add_facts(
        tms_facts
    )


    return evidence



def process_claim(claim_id: str):


    # ---------------------------------
    # Load source systems
    # ---------------------------------

    tms = load_json(
        "04_tms_shipment.json"
    )

    claim_snapshot = load_json(
        "03_claim_snapshot.json"
    )

    erp_invoice = load_csv(
        "05_erp_order_invoice.csv"
    )[0]

    historical_claims = load_csv(
        "12_historical_claims.csv"
    )


    # ---------------------------------
    # Evidence aggregation
    # ---------------------------------

    evidence = build_claim_evidence(
        claim_id
    )


    # ---------------------------------
    # Reconciliation
    # ---------------------------------

    edi_fact = evidence.get_fact(
        "fact.edi_delivered_pieces"
    )

    pod_fact = evidence.get_fact(
        "fact.pod_received_cartons"
    )


    reconciliation = None

    if edi_fact and pod_fact:

        reconciliation = reconcile_delivery_counts(
            edi_fact,
            pod_fact,
        )



    # ---------------------------------
    # Contract Evaluation
    # ---------------------------------

    contract_positions = []


    # Actual commercial value
    # Source: ERP invoice

    invoice_value = erp_invoice.get(
        "extended_value_usd"
    )


    # Shipment weight
    # Source: TMS

    shipment_weight = (
        tms
        .get("shipment", {})
        .get("weight_lb")
    )


    if invoice_value and shipment_weight:

        contract_positions.append(
            cargo_liability_cap(
                invoice_value=Decimal(
                    invoice_value
                ),
                affected_weight_lbs=Decimal(
                    str(shipment_weight)
                ),
            )
        )



    inspection_fact = evidence.get_fact(
        "fact.inspection_cost"
    )

    if inspection_fact:

        contract_positions.append(
            inspection_cost_position(
                inspection_cost=Decimal(
                    inspection_fact.value
                )
            )
        )



    repack_fact = evidence.get_fact(
        "fact.repack_labor"
    )

    if repack_fact:

        contract_positions.append(
            repack_labor_position(
                repack_cost=Decimal(
                    repack_fact.value
                )
            )
        )



    claim_amount = claim_snapshot.get(
        "claim_amount_usd"
    )


    if claim_amount:

        contract_positions.append(
            delay_position(
                requested_amount=Decimal(
                    str(claim_amount)
                ),
                guaranteed_service=(
                    tms
                    .get("service", {})
                    .get("guaranteed")
                ),
            )
        )



    # ---------------------------------
    # Historical Comparator
    # ---------------------------------

    current_claim = {

        "carrier": claim_snapshot.get(
            "carrier"
        ),

        "service_level": (
            tms
            .get("service", {})
            .get("name")
        ),

        "issue_type": " ".join(
            claim_snapshot.get(
                "claim_type_codes",
                []
            )
        ),

        "claimed_usd": str(
            claim_snapshot.get(
                "claim_amount_usd"
            )
        ),

        "evidence": " ".join(
            evidence.source_files()
        ),

    }


    comparables = find_comparables(
        current_claim,
        historical_claims,
    )



    return {

        "claim_id": claim_id,

        "evidence": evidence,

        "reconciliation": reconciliation,

        "contract_position": contract_positions,

        "historical_comparables": comparables,

    }