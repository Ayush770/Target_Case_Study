from evidence import create_fact, fact_to_dict


def test_create_fact_and_serialise():
    fact = create_fact(
        fact_id="fact.pod_received_cartons",
        label="Cartons received",
        value="58",
        source_file="08_proof_of_delivery.pdf",
        locator="page 1; Received 58 of 60 cartons",
        source_role="consignee_signed_receipt",
    )

    result = fact_to_dict(fact)

    assert result["id"] == "fact.pod_received_cartons"
    assert result["value"] == "58"
    assert result["status"] == "verified"
    assert result["anchors"][0]["file"] == "08_proof_of_delivery.pdf"
    assert result["anchors"][0]["confidence"] == 0.99
