from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from typing import Any, cast

import httpx
from psycopg import Connection

from memory_evolutionary_agents.phase2.persistence import PostgresConnectionFactory
from memory_evolutionary_agents.phase4.adapters import HttpQdrantSearchAdapter
from memory_evolutionary_agents.phase4.contracts import (
    ChatQueryFilters,
    ChatQueryRequest,
)
from memory_evolutionary_agents.phase4.linkwalk import ObsidianLinkGraphReader
from memory_evolutionary_agents.phase4.persistence import Phase4Repository
from memory_evolutionary_agents.phase4.service import (
    ChatOrchestrationService,
    LinkWalkRetrievalService,
    VectorRetrievalService,
)
from memory_evolutionary_agents.phase4.synthesis import ChatSynthesisService
from memory_evolutionary_agents.phase4.validation import ChatQueryValidationService


class Phase4IntegrationTestCase(unittest.TestCase):
    def test_dual_retrieval_pipeline_runs_end_to_end(self) -> None:
        if os.getenv("MEA_RUN_INTEGRATION_TESTS", "0") != "1":
            self.skipTest("Set MEA_RUN_INTEGRATION_TESTS=1 to run integration test")

        database_url = os.getenv(
            "MEA_INTEGRATION_DATABASE_URL",
            "postgresql://memory_agents:memory_agents@127.0.0.1:5434/memory_agents_test",
        )
        qdrant_url = os.getenv("MEA_INTEGRATION_QDRANT_URL", "http://127.0.0.1:6334")

        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            vault.mkdir(parents=True, exist_ok=True)
            note_a = vault / "A.md"
            note_b = vault / "B.md"
            note_a.write_text("[[B]] telemetry postgres", encoding="utf-8")
            note_b.write_text("index tuning", encoding="utf-8")

            self._prepare_tables(database_url)
            self._prepare_qdrant_collection(qdrant_url)
            self._seed_memories(database_url, note_a, note_b)
            self._seed_qdrant_points(qdrant_url, note_a)

            repository = Phase4Repository(PostgresConnectionFactory(database_url))
            vector = VectorRetrievalService(
                qdrant_adapter=HttpQdrantSearchAdapter(
                    base_url=qdrant_url,
                    collection_name="memory_chunks",
                    api_key=None,
                ),
                repository=repository,
            )
            linkwalk = LinkWalkRetrievalService(
                graph_reader=ObsidianLinkGraphReader(str(vault)),
                repository=repository,
            )
            service = ChatOrchestrationService(
                validator=ChatQueryValidationService(),
                vector_retrieval=vector,
                linkwalk_retrieval=linkwalk,
                synthesis=ChatSynthesisService(),
                ontology_service=None,
                telemetry_service=None,
            )

            response = service.query(
                ChatQueryRequest(
                    query="telemetry postgres timeout",
                    top_k=4,
                    filters=ChatQueryFilters(project="Telemetry", tags=["database"]),
                )
            )
            self.assertGreaterEqual(len(response.citations), 1)
            self.assertGreater(response.retrieval_diagnostics.vector_candidates, 0)
            self.assertGreaterEqual(response.retrieval_diagnostics.linkwalk_kept, 1)

    def _prepare_tables(self, database_url: str) -> None:
        root = Path(__file__).resolve().parents[1]
        phase2_sql = (root / "migrations/004_phase2_ingestion_core.sql").read_text(
            encoding="utf-8"
        )
        phase3_sql = (root / "migrations/005_phase3_ontology_evolution.sql").read_text(
            encoding="utf-8"
        )
        with Connection.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(cast(Any, phase2_sql))
                cur.execute(cast(Any, phase3_sql))
                cur.execute(
                    cast(Any, "TRUNCATE TABLE schema_proposal_state_events CASCADE")
                )
                cur.execute(cast(Any, "TRUNCATE TABLE schema_proposals CASCADE"))
                cur.execute(cast(Any, "TRUNCATE TABLE relations CASCADE"))
                cur.execute(cast(Any, "TRUNCATE TABLE taxonomy_tags CASCADE"))
                cur.execute(cast(Any, "TRUNCATE TABLE ontology_terms CASCADE"))
                cur.execute(cast(Any, "TRUNCATE TABLE workflow_stage_events CASCADE"))
                cur.execute(cast(Any, "TRUNCATE TABLE memory_chunks CASCADE"))
                cur.execute(cast(Any, "TRUNCATE TABLE canonical_memories CASCADE"))
            conn.commit()

    def _prepare_qdrant_collection(self, qdrant_url: str) -> None:
        create_response = httpx.put(
            f"{qdrant_url}/collections/memory_chunks",
            json={"vectors": {"size": 32, "distance": "Cosine"}},
            timeout=10,
        )
        if create_response.status_code not in {200, 409}:
            create_response.raise_for_status()
        delete_response = httpx.post(
            f"{qdrant_url}/collections/memory_chunks/points/delete",
            json={"filter": {}},
            timeout=10,
        )
        if delete_response.status_code not in {200, 202}:
            delete_response.raise_for_status()

    def _seed_memories(self, database_url: str, note_a: Path, note_b: Path) -> None:
        with Connection.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    cast(
                        Any,
                        """
                        INSERT INTO canonical_memories(
                          source_id, source_path, file_path, content_hash,
                          project, problem, solution, event_date, extraction_confidence,
                          tags, entities, obsidian_note_path, qdrant_point_ids,
                          ontology_terms, taxonomy_tags, relation_edges
                        ) VALUES
                        (1, '/tmp/source', '/tmp/source/a.md', 'a', 'Telemetry', 'p', 's', '2026-04-03', 0.8,
                         '["database"]'::jsonb, '["Postgres"]'::jsonb, %s, '["1001"]'::jsonb,
                         '["Postgres"]'::jsonb, '["database"]'::jsonb, '[]'::jsonb),
                        (1, '/tmp/source', '/tmp/source/b.md', 'b', 'Telemetry', 'p', 's', '2026-04-04', 0.8,
                         '["database"]'::jsonb, '["Index"]'::jsonb, %s, '[]'::jsonb,
                         '["Index"]'::jsonb, '["database"]'::jsonb, '[]'::jsonb)
                        """,
                    ),
                    (str(note_a.resolve()), str(note_b.resolve())),
                )
                cur.execute(
                    cast(
                        Any,
                        """
                        INSERT INTO memory_chunks(memory_id, chunk_id, chunk_index, chunk_text, start_offset, end_offset, vector_size)
                        SELECT id, 'chunk-b-1', 0, 'index tuning removed timeout', 0, 26, 32
                        FROM canonical_memories
                        WHERE file_path = '/tmp/source/b.md'
                        """,
                    )
                )
            conn.commit()

    def _seed_qdrant_points(self, qdrant_url: str, note_a: Path) -> None:
        vector = [0.3 for _ in range(32)]
        response = httpx.put(
            f"{qdrant_url}/collections/memory_chunks/points",
            json={
                "points": [
                    {
                        "id": 1001,
                        "vector": vector,
                        "payload": {
                            "chunk_id": "chunk-a-1",
                            "text": "telemetry postgres timeout fixed",
                            "source_path": "/tmp/source",
                            "file_path": "/tmp/source/a.md",
                            "project": "Telemetry",
                            "event_date": "2026-04-03",
                            "tags": ["database"],
                            "ontology_terms": ["Postgres"],
                            "taxonomy_tags": ["database"],
                            "obsidian_note_path": str(note_a.resolve()),
                        },
                    }
                ]
            },
            timeout=10,
        )
        response.raise_for_status()


if __name__ == "__main__":
    unittest.main()
