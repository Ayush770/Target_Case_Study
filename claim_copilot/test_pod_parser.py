from document_extractor import extract_pdf_text
from pod_parser import parse_pod

text = extract_pdf_text("../08_proof_of_delivery.pdf")

facts = parse_pod(text)

for fact in facts:
    print(fact)

assert len(facts) == 4

values = {fact.id: fact.value for fact in facts}

assert values["fact.pod_received_cartons"] == "58"
assert values["fact.pod_tendered_cartons"] == "60"
assert values["fact.pod_short_cartons"] == "2"
assert values["fact.pod_damaged_cartons"] == "5"

print("POD parser test passed.")