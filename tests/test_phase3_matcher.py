from __future__ import annotations

import unittest

from memory_evolutionary_agents.phase3.contracts import (
    RegistryStatus,
    RegistryTermRecord,
)
from memory_evolutionary_agents.phase3.matcher import OntologyMatcherService


class Phase3MatcherTestCase(unittest.TestCase):
    def test_match_reuses_existing_term_when_threshold_is_met(self) -> None:
        matcher = OntologyMatcherService(threshold=0.8)
        registry = [
            RegistryTermRecord(
                id=1,
                name="Postgres",
                normalized_name="postgres",
                status=RegistryStatus.APPROVED,
                merged_into_id=None,
            )
        ]
        result = matcher.match("postgres", registry)
        self.assertIsNotNone(result.matched)
        if result.matched is not None:
            self.assertEqual(result.matched.name, "Postgres")
        self.assertGreaterEqual(result.confidence, 0.8)

    def test_match_falls_back_to_proposal_when_threshold_not_met(self) -> None:
        matcher = OntologyMatcherService(threshold=0.95)
        registry = [
            RegistryTermRecord(
                id=1,
                name="Postgres",
                normalized_name="postgres",
                status=RegistryStatus.APPROVED,
                merged_into_id=None,
            )
        ]
        result = matcher.match("postgress", registry)
        self.assertIsNone(result.matched)
        self.assertLess(result.confidence, 0.95)


if __name__ == "__main__":
    unittest.main()
