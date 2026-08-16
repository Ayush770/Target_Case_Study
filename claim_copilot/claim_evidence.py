from dataclasses import dataclass, field
from typing import List

try:
    from .evidence import EvidenceFact
except ImportError:  # pragma: no cover - script-style execution fallback
    from evidence import EvidenceFact


@dataclass
class ClaimEvidence:
    """
    Canonical evidence container for a claim.

    All downstream reasoning components consume this object.
    Source systems (PDF, OCR, JSON, CSV) are abstracted away.
    """

    claim_id: str
    facts: List[EvidenceFact] = field(default_factory=list)


    def add_facts(
        self,
        new_facts: List[EvidenceFact],
    ) -> None:
        self.facts.extend(new_facts)


    def get_fact(
        self,
        fact_id: str,
    ) -> EvidenceFact | None:

        for fact in self.facts:
            if fact.id == fact_id:
                return fact

        return None


    def get_all_facts(self) -> List[EvidenceFact]:
        return self.facts


    def source_files(self) -> List[str]:
        """
        Returns unique evidence source documents.
        """

        sources = set()

        for fact in self.facts:
            for anchor in fact.anchors:
                sources.add(anchor.file)

        return sorted(sources)