import json

from tms_evidence_adapter import parse_tms_delivery_fact


with open("../04_tms_shipment.json") as f:
    tms = json.load(f)


facts = parse_tms_delivery_fact(
    tms
)


for fact in facts:
    print(fact)


assert (
    facts[0].id
    == "fact.edi_delivered_pieces"
)

assert (
    facts[0].value
    == "59"
)


print(
    "TMS evidence adapter test passed."
)