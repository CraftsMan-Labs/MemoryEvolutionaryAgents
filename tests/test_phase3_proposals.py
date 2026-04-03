from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import unittest
from typing import Any

from memory_evolutionary_agents.phase3.contracts import (
    ProposalStatus,
    ProposalType,
    RegistryStatus,
    SchemaProposalRecord,
)
from memory_evolutionary_agents.phase3.errors import InvalidProposalTransitionError
from memory_evolutionary_agents.phase3.matcher import OntologyMatcherService
from memory_evolutionary_agents.phase3.service import OntologyEvolutionService


@dataclass
class _FakeRepository:
    proposal: SchemaProposalRecord
    term_status: RegistryStatus | None = None

    def list_ontology_terms(self) -> list[Any]:
        return []

    def list_taxonomy_tags(self) -> list[Any]:
        return []

    def get_proposal(self, proposal_id: int) -> SchemaProposalRecord:
        _ = proposal_id
        return self.proposal

    def update_ontology_term_status(
        self,
        term_id: int,
        status: RegistryStatus,
        merged_into_term_id: int | None,
    ) -> None:
        _ = term_id
        _ = merged_into_term_id
        self.term_status = status

    def update_taxonomy_tag_status(
        self,
        tag_id: int,
        status: RegistryStatus,
        merged_into_tag_id: int | None,
    ) -> None:
        _ = tag_id
        _ = merged_into_tag_id
        self.term_status = status

    def update_proposal_status(
        self,
        proposal_id: int,
        to_status: ProposalStatus,
        changed_by: str,
        note: str | None,
        merged_into_record_id: int | None,
    ) -> SchemaProposalRecord:
        _ = proposal_id
        _ = changed_by
        _ = note
        self.proposal = self.proposal.model_copy(
            update={
                "status": to_status,
                "merged_into_record_id": merged_into_record_id,
            }
        )
        return self.proposal


class Phase3ProposalLifecycleTestCase(unittest.TestCase):
    def test_approve_transitions_provisional_to_approved(self) -> None:
        repository = _FakeRepository(
            proposal=SchemaProposalRecord(
                id=11,
                proposal_type=ProposalType.ONTOLOGY_TERM,
                candidate_value="Postgress",
                normalized_value="postgress",
                confidence=0.7,
                status=ProposalStatus.PROVISIONAL,
                context={},
                linked_record_id=5,
                merged_into_record_id=None,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
            )
        )
        service = OntologyEvolutionService(
            repository=repository, matcher=OntologyMatcherService(threshold=0.82)
        )

        updated = service.approve_proposal(11, actor="reviewer", note=None)

        self.assertEqual(updated.status, ProposalStatus.APPROVED)
        self.assertEqual(repository.term_status, RegistryStatus.APPROVED)

    def test_reject_from_non_provisional_raises_typed_error(self) -> None:
        repository = _FakeRepository(
            proposal=SchemaProposalRecord(
                id=12,
                proposal_type=ProposalType.ONTOLOGY_TERM,
                candidate_value="Postgres",
                normalized_value="postgres",
                confidence=1.0,
                status=ProposalStatus.APPROVED,
                context={},
                linked_record_id=6,
                merged_into_record_id=None,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
            )
        )
        service = OntologyEvolutionService(
            repository=repository, matcher=OntologyMatcherService(threshold=0.82)
        )

        with self.assertRaises(InvalidProposalTransitionError):
            service.reject_proposal(12, actor="reviewer", note="already approved")


if __name__ == "__main__":
    unittest.main()
