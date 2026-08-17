import json

from evidence import create_fact
from reconciliation import (
    reconcile_delivery_counts,
    finding_to_dict,
)


with open("../04_tms_shipment.json") as file:
    tms = json.load(file)


delivered_event = next(
    event
    for event in tms["events"]
    if event["code"] == "DELIVERED"
)


edi_fact = create_fact(
    fact_id="fact.edi_delivered_pieces",
    label="Pieces delivered (EDI)",
    value=str(delivered_event["pieces"]),
    source_file="04_tms_shipment.json",
    locator="events[DELIVERED].pieces",
    source_role="carrier_operational_record",
    status="disputed",
)


pod_fact = create_fact(
    fact_id="fact.pod_received_cartons",
    label="Cartons received (signed POD)",
    value="58",
    source_file="08_proof_of_delivery.pdf",
    locator="page 1; Received 58 of 60 cartons",
    source_role="consignee_signed_receipt",
)


finding = reconcile_delivery_counts(
    edi_fact=edi_fact,
    pod_fact=pod_fact,
)

assert finding is not None

result = finding_to_dict(finding)

print(result)

assert result["id"] == "COUNT_MISMATCH"
assert result["severity"] == "high"
assert result["status"] == "open"
assert "fact.edi_delivered_pieces" in result["facts"]
assert "fact.pod_received_cartons" in result["facts"]

print("Reconciliation test passed.")