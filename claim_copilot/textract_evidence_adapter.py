import re

from evidence import EvidenceFact, EvidenceAnchor


SOURCE_FILE = "09_damage_inspection_report_scanned.pdf"


def create_fact(
    fact_id: str,
    label: str,
    value: str,
    locator: str,
) -> EvidenceFact:
    return EvidenceFact(
        id=fact_id,
        label=label,
        value=value,
        status="verified",
        anchors=[
            EvidenceAnchor(
                file=SOURCE_FILE,
                locator=locator,
                source_role="inspection_report",
                confidence=0.95,
            )
        ],
    )


def parse_inspection_report(text: str) -> list[EvidenceFact]:
    """
    Converts Textract OCR output into canonical EvidenceFact objects.

    This layer only extracts evidence.
    It does not calculate liability or make decisions.
    """

    facts = []

    # --------------------------------------------------
    # Damaged cartons
    # --------------------------------------------------

    if re.search(
        r"Five cartons showed",
        text,
        re.IGNORECASE,
    ):
        facts.append(
            create_fact(
                fact_id="fact.inspection_damaged_cartons",
                label="Damaged cartons",
                value="5",
                locator=(
                    "Five cartons showed crush, puncture "
                    "and/or moisture damage"
                ),
            )
        )


    # --------------------------------------------------
    # Unsellable units
    # --------------------------------------------------

    unsellable_match = re.search(
        r"(\d+)\s+unsellable",
        text,
        re.IGNORECASE,
    )

    if unsellable_match:
        facts.append(
            create_fact(
                fact_id="fact.inspection_unsellable_units",
                label="Unsellable units",
                value=unsellable_match.group(1),
                locator=(
                    "TOTAL: 20 units examined; "
                    f"{unsellable_match.group(1)} unsellable"
                ),
            )
        )


    # --------------------------------------------------
    # Repackable units
    # --------------------------------------------------

    repack_match = re.search(
        r"(\d+)\s+functional but require repacking",
        text,
        re.IGNORECASE,
    )

    if repack_match:
        facts.append(
            create_fact(
                fact_id="fact.inspection_repackable_units",
                label="Repackable units",
                value=repack_match.group(1),
                locator=(
                    f"{repack_match.group(1)} functional "
                    "but require repacking"
                ),
            )
        )


    # --------------------------------------------------
    # Inspection cost
    # --------------------------------------------------

    inspection_match = re.search(
        r"Inspection fee:\s*\$(\d+\.\d+)",
        text,
        re.IGNORECASE,
    )

    if inspection_match:
        facts.append(
            create_fact(
                fact_id="fact.inspection_cost",
                label="Inspection fee",
                value=inspection_match.group(1),
                locator=(
                    f"Inspection fee: ${inspection_match.group(1)}"
                ),
            )
        )


    # --------------------------------------------------
    # Repack labor
    # --------------------------------------------------

    repack_cost_match = re.search(
        r"Repack labor:\s*\$(\d+\.\d+)",
        text,
        re.IGNORECASE,
    )

    if repack_cost_match:
        facts.append(
            create_fact(
                fact_id="fact.repack_labor",
                label="Repack labor",
                value=repack_cost_match.group(1),
                locator=(
                    f"Repack labor: ${repack_cost_match.group(1)}"
                ),
            )
        )


    # --------------------------------------------------
    # Packaging observation
    # --------------------------------------------------

    if re.search(
        r"No vendor packaging specification",
        text,
        re.IGNORECASE,
    ):
        facts.append(
            create_fact(
                fact_id="fact.missing_packaging_specification",
                label="Packaging specification availability",
                value="missing",
                locator=(
                    "No vendor packaging specification "
                    "or laboratory packaging test was provided"
                ),
            )
        )


    # --------------------------------------------------
    # Photo coverage
    # --------------------------------------------------

    photo_match = re.search(
        r"Photos supplied to surveyor:\s*(.+)",
        text,
        re.IGNORECASE,
    )

    if photo_match:
        facts.append(
            create_fact(
                fact_id="fact.inspection_photo_coverage",
                label="Photo coverage",
                value=photo_match.group(1).strip(),
                locator=(
                    "Photos supplied to surveyor"
                ),
            )
        )


    return facts