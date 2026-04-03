from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from typing import Any, cast

from memory_evolutionary_agents.contracts import FileRunRecord
from memory_evolutionary_agents.phase2.contracts import (
    ObsidianWriteResponse,
    QdrantUpsertResponse,
    StageStatus,
    WorkflowExecutionResult,
    WorkflowStatus,
)
from memory_evolutionary_agents.phase2.extraction_service import (
    WorkflowExtractionService,
)
from memory_evolutionary_agents.phase2.service import Phase2IngestionService


class _FakeRunTracking:
    def __init__(self, file_rows: list[FileRunRecord]) -> None:
        self._file_rows = file_rows

    def list_file_runs_for_run(self, run_id: int) -> list[FileRunRecord]:
        _ = run_id
        return self._file_rows


class _FakeRepository:
    def __init__(self) -> None:
        self.stage_events: list[tuple[str, StageStatus]] = []
        self.persisted_memory_calls = 0

    def record_stage_event(self, request) -> None:
        self.stage_events.append((request.stage, request.status))

    def persist_memory(self, request):
        _ = request
        self.persisted_memory_calls += 1
        return type("Result", (), {"memory_id": 1})()

    def persist_chunk(self, request) -> None:
        _ = request


@dataclass
class _FakeWorkflowRunner:
    result: WorkflowExecutionResult

    def run_workflow(self, request):
        _ = request
        return self.result


class _FakeQdrantAdapter:
    def upsert(self, request):
        ids = [point.point_id for point in request.points]
        return QdrantUpsertResponse(stored_point_ids=ids)


class _FakeObsidianAdapter:
    def write_summary(self, request):
        _ = request
        return ObsidianWriteResponse(note_path="/tmp/note.md")


class Phase2ServiceTestCase(unittest.TestCase):
    def test_execute_for_run_records_success_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "note.md"
            file_path.write_text("phase2 test", encoding="utf-8")

            file_row = FileRunRecord(
                id=101,
                run_id=100,
                source_id=1,
                source_path=temp_dir,
                file_path=str(file_path),
                stage="discovered",
                status="queued",
                error_code=None,
                error_message=None,
                created_at=datetime.now(tz=timezone.utc),
            )
            run_tracking = _FakeRunTracking([file_row])
            repository = _FakeRepository()
            runner = _FakeWorkflowRunner(
                result=WorkflowExecutionResult(
                    status=WorkflowStatus.SUCCESS,
                    raw_output={
                        "terminal_output": {
                            "confidence": 0.8,
                            "tags": [],
                            "entities": [],
                            "qdrant_point_ids": [],
                        }
                    },
                )
            )
            service = Phase2IngestionService(
                cast(Any, run_tracking),
                cast(Any, repository),
                cast(Any, runner),
                WorkflowExtractionService(),
                cast(Any, _FakeQdrantAdapter()),
                cast(Any, _FakeObsidianAdapter()),
            )

            service.execute_for_run(100)

            self.assertEqual(repository.persisted_memory_calls, 1)
            self.assertEqual(repository.stage_events[0][0], "workflow_started")
            self.assertEqual(repository.stage_events[-1][0], "workflow_completed")


if __name__ == "__main__":
    unittest.main()
