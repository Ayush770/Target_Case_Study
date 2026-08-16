from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class EvidenceAnchor:
    file: str
    locator: str
    source_role: str
    confidence: float


@dataclass(frozen=True)
class EvidenceFact:
    id: str
    label: str
    value: str
    status: str
    anchors: list[EvidenceAnchor]


def create_fact(
    fact_id: str,
    label: str,
    value: str,
    source_file: str,
    locator: str,
    source_role: str,
    confidence: float = 0.99,
    status: str = "verified",
) -> EvidenceFact:
    return EvidenceFact(
        id=fact_id,
        label=label,
        value=value,
        status=status,
        anchors=[
            EvidenceAnchor(
                file=source_file,
                locator=locator,
                source_role=source_role,
                confidence=confidence,
            )
        ],
    )


def fact_to_dict(fact: EvidenceFact) -> dict:
    return asdict(fact)