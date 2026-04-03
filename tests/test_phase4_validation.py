from __future__ import annotations

import unittest

from memory_evolutionary_agents.phase4.contracts import (
    ChatQueryFilters,
    ChatQueryRequest,
)
from memory_evolutionary_agents.phase4.errors import Phase4ValidationError
from memory_evolutionary_agents.phase4.validation import ChatQueryValidationService


class Phase4ValidationTestCase(unittest.TestCase):
    def test_validation_rejects_invalid_date_range(self) -> None:
        validator = ChatQueryValidationService()
        request = ChatQueryRequest(
            query="find postgres issue",
            filters=ChatQueryFilters(
                project="Telemetry",
                event_date_from="2026-05-01",
                event_date_to="2026-04-01",
            ),
        )
        with self.assertRaises(Phase4ValidationError):
            validator.validate(request)

    def test_validation_rejects_date_only_filter(self) -> None:
        validator = ChatQueryValidationService()
        request = ChatQueryRequest(
            query="find by date",
            filters=ChatQueryFilters(event_date_from="2026-04-01"),
        )
        with self.assertRaises(Phase4ValidationError):
            validator.validate(request)

    def test_validation_normalizes_whitespace_and_duplicates(self) -> None:
        validator = ChatQueryValidationService()
        request = ChatQueryRequest(
            query="  search memory  ",
            filters=ChatQueryFilters(
                project="  Telemetry  ",
                tags=["db", " DB ", ""],
                ontology_terms=["Postgres", "postgres"],
            ),
        )
        validated = validator.validate(request)
        self.assertEqual(validated.query, "search memory")
        self.assertEqual(validated.filters.project, "Telemetry")
        self.assertEqual(validated.filters.tags, ["db"])
        self.assertEqual(validated.filters.ontology_terms, ["Postgres"])


if __name__ == "__main__":
    unittest.main()
