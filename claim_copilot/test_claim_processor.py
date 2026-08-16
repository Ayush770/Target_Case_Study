from claim_processor import process_claim


result = process_claim(
    "CLAIM-001"
)


print("\nCLAIM ID")
print(result["claim_id"])


print("\nEVIDENCE FACTS")
for fact in result["evidence"].get_all_facts():
    print(fact)


print("\nRECONCILIATION")
print(result["reconciliation"])


print("\nCONTRACT POSITION")
for item in result["contract_position"]:
    print(item)


print("\nHISTORICAL COMPARABLES")

for item in result["historical_comparables"]:
    print(
        item.claim_id,
        item.score,
        item.settled
    )


print("\nClaim processor test passed.")