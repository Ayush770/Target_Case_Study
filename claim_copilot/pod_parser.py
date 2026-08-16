import re

try:
    from .evidence import create_fact
except ImportError:  # pragma: no cover - script-style execution fallback
    from evidence import create_fact


def parse_pod(text: str):
    facts = []

    received = re.search(r"Received\s+(\d+)\s+of\s+(\d+)\s+cartons", text)
    short = re.search(r"(\d+)\s+cartons short", text)
    damaged = re.search(r"(\d+)\s+cartons crushed/wet", text)

    if received:
        facts.append(
            create_fact(
                fact_id="fact.pod_received_cartons",
                label="Cartons received",
                value=received.group(1),
                source_file="08_proof_of_delivery.pdf",
                locator="page 1; Received 58 of 60 cartons",
                source_role="consignee_signed_receipt",
            )
        )

        facts.append(
            create_fact(
                fact_id="fact.pod_tendered_cartons",
                label="Cartons tendered",
                value=received.group(2),
                source_file="08_proof_of_delivery.pdf",
                locator="page 1; Received 58 of 60 cartons",
                source_role="consignee_signed_receipt",
            )
        )

    if short:
        facts.append(
            create_fact(
                fact_id="fact.pod_short_cartons",
                label="Short cartons",
                value=short.group(1),
                source_file="08_proof_of_delivery.pdf",
                locator="page 1; 2 cartons short",
                source_role="consignee_signed_receipt",
            )
        )

    if damaged:
        facts.append(
            create_fact(
                fact_id="fact.pod_damaged_cartons",
                label="Damaged cartons",
                value=damaged.group(1),
                source_file="08_proof_of_delivery.pdf",
                locator="page 1; 5 cartons crushed/wet",
                source_role="consignee_signed_receipt",
            )
        )

    return facts