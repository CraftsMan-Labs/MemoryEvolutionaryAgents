from __future__ import annotations

import unittest
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient

from memory_evolutionary_agents.api import create_app
from memory_evolutionary_agents.container import AppContainer
from memory_evolutionary_agents.phase4.contracts import (
    ChatQueryResponse,
    CitationRecord,
    RetrievalDiagnostics,
)


class _FakeOnboarding:
    def is_completed(self) -> bool:
        return True


class _FakeChatService:
    def query(self, request):
        _ = request
        return ChatQueryResponse(
            answer="Answer for query: test",
            confidence=0.7,
            citations=[
                CitationRecord(
                    source_path="/tmp/source",
                    note_path="/tmp/vault/a.md",
                    chunk_id="chunk-1",
                )
            ],
            retrieval_diagnostics=RetrievalDiagnostics(
                vector_candidates=8,
                vector_kept=1,
                linkwalk_candidates=2,
                linkwalk_kept=1,
                resolved_ontology_aliases={"Postgress": "Postgres"},
                resolved_taxonomy_aliases={},
            ),
        )


def _container(chat_service: _FakeChatService | None) -> AppContainer:
    return AppContainer(
        settings=cast(Any, None),
        database=cast(Any, None),
        source_registry=cast(Any, None),
        run_tracking=cast(Any, None),
        onboarding=cast(Any, _FakeOnboarding()),
        scanner=cast(Any, None),
        scheduler=cast(Any, None),
        phase2_ingestion=cast(Any, None),
        phase3_ontology=cast(Any, None),
        phase4_chat=cast(Any, chat_service),
        phase5_telemetry=None,
        phase5_status=None,
        phase6_progress=cast(Any, None),
    )


class Phase4ApiTestCase(unittest.TestCase):
    def test_chat_query_route_returns_response(self) -> None:
        with patch(
            "memory_evolutionary_agents.api.build_container",
            return_value=_container(_FakeChatService()),
        ):
            client = TestClient(create_app())
            response = client.post(
                "/chat/query",
                json={
                    "query": "test",
                    "filters": {"project": "Telemetry"},
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["confidence"], 0.7)
            self.assertEqual(payload["citations"][0]["chunk_id"], "chunk-1")

    def test_chat_query_route_returns_404_when_disabled(self) -> None:
        with patch(
            "memory_evolutionary_agents.api.build_container",
            return_value=_container(None),
        ):
            client = TestClient(create_app())
            response = client.post("/chat/query", json={"query": "test"})
            self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
