"""Gold-case checks for the supplied candidate pack."""

import unittest

from app import build_case, build_draft


class ClaimCopilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = build_case()

    def test_key_counts_are_preserved(self):
        values = {fact["id"]: fact["value"] for fact in self.case["facts"]}
        self.assertEqual(values["fact.tendered_cartons"], "60")
        self.assertEqual(values["fact.pod_received_cartons"], "58")
        self.assertEqual(values["fact.edi_delivered_pieces"], "59")

    def test_required_findings_are_present(self):
        finding_ids = {finding["id"] for finding in self.case["findings"]}
        self.assertSetEqual(
            finding_ids,
            {"COUNT_MISMATCH", "PARTIAL_PHOTO_COVERAGE", "MISSING_PACKAGING_SPEC"},
        )

    def test_contract_position_does_not_overstate_delay_right(self):
        self.assertIn("excluded", self.case["position"]["delay_markdown"]["status"])
        self.assertEqual(self.case["position"]["direct_cargo"]["amount"], "$9,350.00")

    def test_draft_is_validated_and_requires_approval(self):
        draft = build_draft(self.case)
        self.assertEqual(draft["validation"]["citation_coverage"], "pass")
        self.assertEqual(draft["validation"]["numeric_consistency"], "pass")
        self.assertTrue(draft["validation"]["approval_required"])


if __name__ == "__main__":
    unittest.main()
