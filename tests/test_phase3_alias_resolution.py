from __future__ import annotations

from dataclasses import dataclass
import unittest

from memory_evolutionary_agents.phase3.contracts import (
    FilterAliasResolutionRequest,
    RegistryStatus,
    RegistryTermRecord,
)
from memory_evolutionary_agents.phase3.matcher import OntologyMatcherService
from memory_evolutionary_agents.phase3.service import OntologyEvolutionService


@dataclass
class _FakeAliasRepository:
    def list_ontology_terms(self):
        return []

    def list_taxonomy_tags(self):
        return []

    def find_ontology_term_by_normalized(self, normalized_name: str):
        mapping = {
            "postgress": RegistryTermRecord(
                id=2,
                name="Postgress",
                normalized_name="postgress",
                status=RegistryStatus.MERGED,
                merged_into_id=1,
            ),
            "postgres": RegistryTermRecord(
                id=1,
                name="Postgres",
                normalized_name="postgres",
                status=RegistryStatus.APPROVED,
                merged_into_id=None,
            ),
        }
        return mapping.get(normalized_name)

    def get_ontology_term_by_id(self, term_id: int):
        if term_id == 1:
            return RegistryTermRecord(
                id=1,
                name="Postgres",
                normalized_name="postgres",
                status=RegistryStatus.APPROVED,
                merged_into_id=None,
            )
        return None

    def find_taxonomy_tag_by_normalized(self, normalized_name: str):
        mapping = {
            "db": RegistryTermRecord(
                id=5,
                name="DB",
                normalized_name="db",
                status=RegistryStatus.MERGED,
                merged_into_id=6,
            ),
            "database": RegistryTermRecord(
                id=6,
                name="Database",
                normalized_name="database",
                status=RegistryStatus.APPROVED,
                merged_into_id=None,
            ),
        }
        return mapping.get(normalized_name)

    def get_taxonomy_tag_by_id(self, tag_id: int):
        if tag_id == 6:
            return RegistryTermRecord(
                id=6,
                name="Database",
                normalized_name="database",
                status=RegistryStatus.APPROVED,
                merged_into_id=None,
            )
        return None


class Phase3AliasResolutionTestCase(unittest.TestCase):
    def test_alias_resolution_maps_merged_values_to_canonical_targets(self) -> None:
        service = OntologyEvolutionService(
            repository=_FakeAliasRepository(),
            matcher=OntologyMatcherService(threshold=0.82),
        )

        resolved = service.resolve_filter_aliases(
            FilterAliasResolutionRequest(
                ontology_terms=["Postgress", "UnknownTerm"],
                taxonomy_tags=["DB", "new-tag"],
            )
        )

        self.assertEqual(resolved.ontology_aliases["Postgress"], "Postgres")
        self.assertEqual(resolved.ontology_aliases["UnknownTerm"], "UnknownTerm")
        self.assertEqual(resolved.taxonomy_aliases["DB"], "Database")
        self.assertIn("Postgres", resolved.ontology_terms)
        self.assertIn("UnknownTerm", resolved.ontology_terms)
        self.assertIn("Database", resolved.taxonomy_tags)


if __name__ == "__main__":
    unittest.main()
