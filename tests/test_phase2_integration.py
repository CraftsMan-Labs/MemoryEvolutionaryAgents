from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import httpx
from psycopg import Connection

from memory_evolutionary_agents.contracts import FileRunRecord
from memory_evolutionary_agents.phase2.adapters import (
    FileSystemObsidianAdapter,
    HttpQdrantAdapter,
)
from memory_evolutionary_agents.phase2.contracts import (
    WorkflowExecutionResult,
    WorkflowStatus,
)
from memory_evolutionary_agents.phase2.extraction_service import (
    WorkflowExtractionService,
)
from memory_evolutionary_agents.phase2.persistence import (
    Phase2Repository,
    PostgresConnectionFactory,
)
from memory_evolutionary_agents.phase2.service import Phase2IngestionService


class _FakeRunTracking:
    def __init__(self, file_rows: list[FileRunRecord]) -> None:
        self._file_rows = file_rows

    def list_file_runs_for_run(self, run_id: int) -> list[FileRunRecord]:
        _ = run_id
        return self._file_rows


@dataclass
class _FakeWorkflowRunner:
    result: WorkflowExecutionResult

    def run_workflow(self, request: Any) -> WorkflowExecutionResult:
        _ = request
        return self.result


class Phase2IntegrationTestCase(unittest.TestCase):
    def test_end_to_end_persists_postgres_and_updates_qdrant_and_obsidian(self) -> None:
        if os.getenv("MEA_RUN_INTEGRATION_TESTS", "0") != "1":
            self.skipTest("Set MEA_RUN_INTEGRATION_TESTS=1 to run integration test")

        database_url = os.getenv(
            "MEA_INTEGRATION_DATABASE_URL",
            "postgresql://memory_agents:memory_agents@127.0.0.1:5434/memory_agents_test",
        )
        qdrant_url = os.getenv("MEA_INTEGRATION_QDRANT_URL", "http://127.0.0.1:6334")

        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir(parents=True, exist_ok=True)
            file_path = source_dir / "memory.md"
            file_path.write_text("integration memory", encoding="utf-8")

            self._prepare_tables(database_url)
            self._prepare_qdrant_collection(qdrant_url)

            repository = Phase2Repository(PostgresConnectionFactory(database_url))
            run_tracking = _FakeRunTracking(
                [
                    FileRunRecord(
                        id=501,
                        run_id=500,
                        source_id=1,
                        source_path=str(source_dir),
                        file_path=str(file_path),
                        stage="discovered",
                        status="queued",
                        error_code=None,
                        error_message=None,
                        created_at=datetime.now(tz=timezone.utc),
                    )
                ]
            )
            runner = _FakeWorkflowRunner(
                result=WorkflowExecutionResult(
                    status=WorkflowStatus.SUCCESS,
                    raw_output={
                        "terminal_output": {
                            "project": "Integration",
                            "problem": "Test problem",
                            "solution": "Test solution",
                            "date": "2026-04-03",
                            "confidence": 0.88,
                            "tags": ["integration"],
                            "entities": ["postgres", "qdrant"],
                            "qdrant_point_ids": [],
                            "chunks": [
                                {
                                    "chunk_id": "chunk-integration-1",
                                    "chunk_index": 0,
                                    "text": "integration memory",
                                    "start_offset": 0,
                                    "end_offset": 18,
                                }
                            ],
                            "embeddings": [
                                {
                                    "chunk_id": "chunk-integration-1",
                                    "vector": [0.1, 0.2, 0.3],
                                    "model_name": "deterministic-hash-embeddings-v1",
                                }
                            ],
                        }
                    },
                )
            )

            service = Phase2IngestionService(
                run_tracking=cast(Any, run_tracking),
                repository=repository,
                workflow_runner=cast(Any, runner),
                extraction_service=WorkflowExtractionService(),
                qdrant_adapter=HttpQdrantAdapter(
                    base_url=qdrant_url,
                    collection_name="memory_chunks",
                    api_key=None,
                ),
                obsidian_adapter=FileSystemObsidianAdapter(temp_dir),
            )
            service.execute_for_run(500)

            count_response = httpx.post(
                f"{qdrant_url}/collections/memory_chunks/points/count",
                json={"exact": True},
                timeout=10,
            )
            count_response.raise_for_status()
            point_count = int(count_response.json().get("result", {}).get("count", 0))
            self.assertGreaterEqual(point_count, 1)

            with Connection.connect(database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) AS count FROM canonical_memories")
                    memory_count_row = cur.fetchone()
                    memory_count = (
                        int(memory_count_row[0]) if memory_count_row is not None else 0
                    )
                    cur.execute("SELECT COUNT(*) AS count FROM memory_chunks")
                    chunk_count_row = cur.fetchone()
                    chunk_count = (
                        int(chunk_count_row[0]) if chunk_count_row is not None else 0
                    )
                    cur.execute("SELECT COUNT(*) AS count FROM workflow_stage_events")
                    event_count_row = cur.fetchone()
                    event_count = (
                        int(event_count_row[0]) if event_count_row is not None else 0
                    )

            self.assertGreaterEqual(memory_count, 1)
            self.assertGreaterEqual(chunk_count, 1)
            self.assertGreaterEqual(event_count, 2)
            expected_note = Path(temp_dir) / "memory-agent-summaries" / "memory.md.md"
            self.assertTrue(expected_note.exists())

    def _prepare_tables(self, database_url: str) -> None:
        phase2_migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations/004_phase2_ingestion_core.sql"
        )
        phase3_migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations/005_phase3_ontology_evolution.sql"
        )
        phase2_sql = phase2_migration_path.read_text(encoding="utf-8")
        phase3_sql = phase3_migration_path.read_text(encoding="utf-8")
        with Connection.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(cast(Any, phase2_sql))
                cur.execute(cast(Any, phase3_sql))
                cur.execute("TRUNCATE TABLE schema_proposal_state_events CASCADE")
                cur.execute("TRUNCATE TABLE schema_proposals CASCADE")
                cur.execute("TRUNCATE TABLE relations CASCADE")
                cur.execute("TRUNCATE TABLE taxonomy_tags CASCADE")
                cur.execute("TRUNCATE TABLE ontology_terms CASCADE")
                cur.execute("TRUNCATE TABLE workflow_stage_events CASCADE")
                cur.execute("TRUNCATE TABLE memory_chunks CASCADE")
                cur.execute("TRUNCATE TABLE canonical_memories CASCADE")
            conn.commit()

    def _prepare_qdrant_collection(self, qdrant_url: str) -> None:
        create_response = httpx.put(
            f"{qdrant_url}/collections/memory_chunks",
            json={
                "vectors": {
                    "size": 3,
                    "distance": "Cosine",
                }
            },
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


if __name__ == "__main__":
    unittest.main()
