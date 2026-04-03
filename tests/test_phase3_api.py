from __future__ import annotations

from datetime import datetime, timezone
import unittest
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient

from memory_evolutionary_agents.api import create_app
from memory_evolutionary_agents.container import AppContainer
from memory_evolutionary_agents.phase3.contracts import (
    ProposalDetailResponse,
    ProposalStatus,
    ProposalType,
    SchemaProposalRecord,
    SchemaProposalStateEventRecord,
)
from memory_evolutionary_agents.phase3.errors import InvalidProposalTransitionError


class _FakeOnboarding:
    def __init__(self, completed: bool) -> None:
        self._completed = completed

    def is_completed(self) -> bool:
        return self._completed


class _FakePhase3Service:
    def __init__(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self._proposal = SchemaProposalRecord(
            id=101,
            proposal_type=ProposalType.ONTOLOGY_TERM,
            candidate_value="Postgress",
            normalized_value="postgress",
            confidence=0.71,
            status=ProposalStatus.PROVISIONAL,
            context={"file_path": "/tmp/memory.md"},
            linked_record_id=31,
            merged_into_record_id=None,
            created_at=now,
            updated_at=now,
        )

    def list_proposals(
        self,
        status: ProposalStatus | None,
        proposal_type: ProposalType | None,
        limit: int,
    ) -> list[SchemaProposalRecord]:
        _ = (status, proposal_type, limit)
        return [self._proposal]

    def get_proposal_detail(self, proposal_id: int) -> ProposalDetailResponse:
        _ = proposal_id
        event = SchemaProposalStateEventRecord(
            id=1,
            proposal_id=self._proposal.id,
            from_status=None,
            to_status=ProposalStatus.PROVISIONAL,
            changed_by="worker",
            note=None,
            changed_at=self._proposal.created_at,
        )
        return ProposalDetailResponse(proposal=self._proposal, events=[event])

    def approve_proposal(
        self,
        proposal_id: int,
        actor: str,
        note: str | None,
    ) -> SchemaProposalRecord:
        _ = (proposal_id, actor, note)
        self._proposal = self._proposal.model_copy(
            update={"status": ProposalStatus.APPROVED}
        )
        return self._proposal

    def reject_proposal(
        self,
        proposal_id: int,
        actor: str,
        note: str | None,
    ) -> SchemaProposalRecord:
        _ = (proposal_id, actor, note)
        raise InvalidProposalTransitionError(
            "only provisional proposals can be transitioned"
        )

    def merge_proposal(
        self,
        proposal_id: int,
        target_record_id: int,
        actor: str,
        note: str | None,
    ) -> SchemaProposalRecord:
        _ = (proposal_id, target_record_id, actor, note)
        self._proposal = self._proposal.model_copy(
            update={
                "status": ProposalStatus.MERGED,
                "merged_into_record_id": target_record_id,
            }
        )
        return self._proposal


def _build_container(phase3_service: _FakePhase3Service | None) -> AppContainer:
    return AppContainer(
        settings=cast(Any, None),
        database=cast(Any, None),
        source_registry=cast(Any, None),
        run_tracking=cast(Any, None),
        onboarding=cast(Any, _FakeOnboarding(completed=True)),
        scanner=cast(Any, None),
        scheduler=cast(Any, None),
        phase2_ingestion=cast(Any, None),
        phase3_ontology=cast(Any, phase3_service),
        phase4_chat=cast(Any, None),
        phase5_telemetry=None,
        phase5_status=None,
        phase6_progress=cast(Any, None),
    )


class Phase3ApiTestCase(unittest.TestCase):
    def test_proposal_routes_cover_list_detail_and_state_changes(self) -> None:
        fake_service = _FakePhase3Service()
        with patch(
            "memory_evolutionary_agents.api.build_container",
            return_value=_build_container(fake_service),
        ):
            client = TestClient(create_app())

            list_response = client.get("/ontology/proposals")
            self.assertEqual(list_response.status_code, 200)
            self.assertEqual(len(list_response.json()["proposals"]), 1)

            detail_response = client.get("/ontology/proposals/101")
            self.assertEqual(detail_response.status_code, 200)
            self.assertEqual(detail_response.json()["proposal"]["id"], 101)

            approve_response = client.post(
                "/ontology/proposals/101/approve",
                json={"actor": "reviewer", "note": "looks good"},
            )
            self.assertEqual(approve_response.status_code, 200)
            self.assertEqual(approve_response.json()["status"], "approved")

            merge_response = client.post(
                "/ontology/proposals/101/merge",
                json={"actor": "reviewer", "target_record_id": 9, "note": "dedupe"},
            )
            self.assertEqual(merge_response.status_code, 200)
            self.assertEqual(merge_response.json()["status"], "merged")
            self.assertEqual(merge_response.json()["merged_into_record_id"], 9)

    def test_reject_route_returns_400_on_invalid_transition(self) -> None:
        fake_service = _FakePhase3Service()
        with patch(
            "memory_evolutionary_agents.api.build_container",
            return_value=_build_container(fake_service),
        ):
            client = TestClient(create_app())
            reject_response = client.post(
                "/ontology/proposals/101/reject",
                json={"actor": "reviewer", "note": "invalid"},
            )
            self.assertEqual(reject_response.status_code, 400)

    def test_routes_return_404_when_phase3_service_is_disabled(self) -> None:
        with patch(
            "memory_evolutionary_agents.api.build_container",
            return_value=_build_container(None),
        ):
            client = TestClient(create_app())
            response = client.get("/ontology/proposals")
            self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
