try:
    from .evidence import EvidenceFact, EvidenceAnchor
except ImportError:  # pragma: no cover - script-style execution fallback
    from evidence import EvidenceFact, EvidenceAnchor


def parse_tms_delivery_fact(
    tms_data: dict,
):
    """
    Converts carrier TMS / EDI delivery information
    into canonical EvidenceFact objects.
    """

    facts = []

    for event in tms_data.get("events", []):

        if (
            event.get("code") == "DELIVERED"
            and event.get("source") == "EDI 214"
            and event.get("pieces") is not None
        ):

            facts.append(
                EvidenceFact(
                    id="fact.edi_delivered_pieces",
                    label="EDI delivered pieces",
                    value=str(
                        event["pieces"]
                    ),
                    status="verified",
                    anchors=[
                        EvidenceAnchor(
                            file="04_tms_shipment.json",
                            locator=(
                                "DELIVERED event "
                                "from EDI 214"
                            ),
                            source_role="carrier_edi",
                            confidence=0.95,
                        )
                    ],
                )
            )

    return facts