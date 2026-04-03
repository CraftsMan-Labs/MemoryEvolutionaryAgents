from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from psycopg import Connection

from memory_evolutionary_agents.contracts import FileRunRecord
from memory_evolutionary_agents.phase2.contracts import (
    ObsidianWriteResponse,
    QdrantUpsertResponse,
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
from memory_evolutionary_agents.phase3.contracts import ProposalStatus, RegistryStatus
from memory_evolutionary_agents.phase3.contracts import FilterAliasResolutionRequest
from memory_evolutionary_agents.phase3.matcher import OntologyMatcherService
from memory_evolutionary_agents.phase3.persistence import Phase3Repository
from memory_evolutionary_agents.phase3.service import OntologyEvolutionService


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


class _FakeQdrantAdapter:
    def upsert(self, request: Any) -> QdrantUpsertResponse:
        stored_ids = [point.point_id for point in request.points]
        return QdrantUpsertResponse(stored_point_ids=stored_ids)


class _FakeObsidianAdapter:
    def write_summary(self, request: Any) -> ObsidianWriteResponse:
        _ = request
        return ObsidianWriteResponse(note_path="/tmp/phase3-summary.md")


class Phase3IntegrationTestCase(unittest.TestCase):
    def test_ingest_creates_proposals_and_merge_updates_registry(self) -> None:
        if os.getenv("MEA_RUN_INTEGRATION_TESTS", "0") != "1":
            self.skipTest("Set MEA_RUN_INTEGRATION_TESTS=1 to run integration test")

        database_url = os.getenv(
            "MEA_INTEGRATION_DATABASE_URL",
            "postgresql://memory_agents:memory_agents@127.0.0.1:5434/memory_agents_test",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir(parents=True, exist_ok=True)
            file_path = source_dir / "ontology-memory.md"
            file_path.write_text("phase3 integration memory", encoding="utf-8")

            self._prepare_tables(database_url)

            phase2_repository = Phase2Repository(
                PostgresConnectionFactory(database_url)
            )
            phase3_repository = Phase3Repository(
                PostgresConnectionFactory(database_url)
            )
            phase3_service = OntologyEvolutionService(
                repository=phase3_repository,
                matcher=OntologyMatcherService(threshold=0.95),
            )

            run_tracking = _FakeRunTracking(
                [
                    FileRunRecord(
                        id=801,
                        run_id=800,
                        source_id=21,
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
                            "project": "Telemetry",
                            "problem": "Mismatch",
                            "solution": "Merge",
                            "date": "2026-04-03",
                            "confidence": 0.9,
                            "tags": ["database"],
                            "entities": ["Postgress"],
                            "qdrant_point_ids": [],
                            "chunks": [
                                {
                                    "chunk_id": "chunk-phase3-1",
                                    "chunk_index": 0,
                                    "text": "phase3 integration memory",
                                    "start_offset": 0,
                                    "end_offset": 25,
                                }
                            ],
                            "embeddings": [
                                {
                                    "chunk_id": "chunk-phase3-1",
                                    "vector": [0.1, 0.2, 0.3],
                                    "model_name": "deterministic-hash-embeddings-v1",
                                }
                            ],
                        }
                    },
                )
            )
            ingestion_service = Phase2IngestionService(
                run_tracking=cast(Any, run_tracking),
                repository=phase2_repository,
                workflow_runner=cast(Any, runner),
                extraction_service=WorkflowExtractionService(),
                qdrant_adapter=cast(Any, _FakeQdrantAdapter()),
                obsidian_adapter=cast(Any, _FakeObsidianAdapter()),
                ontology_service=phase3_service,
            )
            ingestion_service.execute_for_run(800)

            proposals = phase3_service.list_proposals(
                status=ProposalStatus.PROVISIONAL,
                proposal_type=None,
                limit=20,
            )
            self.assertGreaterEqual(len(proposals), 2)

            canonical = self._fetch_single_value(
                database_url,
                "SELECT ontology_terms FROM canonical_memories LIMIT 1",
            )
            self.assertIsInstance(canonical, list)
            if isinstance(canonical, list):
                self.assertIn("Telemetry", canonical)

            approved_target = phase3_repository.upsert_ontology_term(
                name="Postgres",
                status=RegistryStatus.APPROVED,
            )
            typo_proposal = next(
                proposal
                for proposal in proposals
                if proposal.candidate_value.lower() == "postgress"
            )
            merged = phase3_service.merge_proposal(
                proposal_id=typo_proposal.id,
                target_record_id=approved_target.id,
                actor="reviewer",
                note="dedupe typo",
            )
            self.assertEqual(merged.status, ProposalStatus.MERGED)

            resolved_filters = phase3_service.resolve_filter_aliases(
                FilterAliasResolutionRequest(
                    ontology_terms=["Postgress"],
                    taxonomy_tags=["database"],
                )
            )
            self.assertEqual(
                resolved_filters.ontology_aliases["Postgress"],
                "Postgres",
            )
            self.assertIn("Postgres", resolved_filters.ontology_terms)

            merged_target_id = self._fetch_single_value(
                database_url,
                "SELECT merged_into_term_id FROM ontology_terms WHERE normalized_name = 'postgress'",
            )
            self.assertEqual(cast(int, merged_target_id), approved_target.id)

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

    def _fetch_single_value(self, database_url: str, query: str) -> object:
        with Connection.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(cast(Any, query))
                row = cur.fetchone()
        if row is None:
            raise RuntimeError("expected query row")
        return row[0]


if __name__ == "__main__":
    unittest.main()
