from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import unittest
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient

from memory_evolutionary_agents.api import create_app
from memory_evolutionary_agents.container import AppContainer
from memory_evolutionary_agents.phase6.contracts import (
    FileProgressRecord,
    FileRetryRequest,
    FileStage,
    FileTimelineEvent,
    FileTimelineResponse,
    RetryScheduleResult,
    RunFilesQuery,
    RunFilesResponse,
)


class _FakeOnboarding:
    def is_completed(self) -> bool:
        return True


class _FakePhase6Progress:
    def list_run_files(self, run_id: int, query: RunFilesQuery) -> RunFilesResponse:
        _ = query
        now = datetime.now(tz=timezone.utc)
        return RunFilesResponse(
            run_id=run_id,
            files=[
                FileProgressRecord(
                    file_run_id=1,
                    run_id=run_id,
                    source_id=10,
                    source_path="/tmp/source",
                    file_path="/tmp/source/a.md",
                    stage=FileStage.FAILED,
                    status="failed",
                    error_code="workflow_failed",
                    error_message="boom",
                    created_at=now,
                )
            ],
            stage_summary=[],
            status_summary=[],
        )

    def timeline(self, file_run_id: int) -> FileTimelineResponse:
        return FileTimelineResponse(
            file_run_id=file_run_id,
            events=[
                FileTimelineEvent(
                    id=1,
                    run_id=7,
                    file_run_id=file_run_id,
                    source_id=10,
                    file_path="/tmp/source/a.md",
                    from_stage=None,
                    to_stage=FileStage.DISCOVERED,
                    status="queued",
                    duration_ms=None,
                    error_code=None,
                    error_message=None,
                    recorded_at=datetime.now(tz=timezone.utc),
                )
            ],
        )

    def manual_retry(
        self,
        file_run_id: int,
        request: FileRetryRequest,
    ) -> RetryScheduleResult:
        _ = request
        return RetryScheduleResult(
            file_run_id=file_run_id,
            attempt_count=1,
            next_attempt_at=datetime.now(tz=timezone.utc),
            status="queued",
        )

    def dead_letter_items(self, limit: int) -> list[Any]:
        _ = limit
        return []

    def subscribe(self, run_id: int) -> Any:
        _ = run_id
        queue: asyncio.Queue[str] = asyncio.Queue()
        queue.put_nowait('{"type":"stage_event"}')
        return queue

    def unsubscribe(self, run_id: int, queue: Any) -> None:
        _ = (run_id, queue)


def _container() -> AppContainer:
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
        phase4_chat=cast(Any, None),
        phase5_telemetry=cast(Any, None),
        phase5_status=cast(Any, None),
        phase6_progress=cast(Any, _FakePhase6Progress()),
    )


class Phase6ApiTestCase(unittest.TestCase):
    def test_progress_routes_return_payloads(self) -> None:
        with patch(
            "memory_evolutionary_agents.api.build_container",
            return_value=_container(),
        ):
            client = TestClient(create_app())

            files_response = client.get("/runs/7/files")
            self.assertEqual(files_response.status_code, 200)
            self.assertEqual(files_response.json()["run_id"], 7)

            timeline_response = client.get("/files/1/timeline")
            self.assertEqual(timeline_response.status_code, 200)
            self.assertEqual(timeline_response.json()["file_run_id"], 1)

            retry_response = client.post(
                "/files/1/retry", json={"requested_by": "operator"}
            )
            self.assertEqual(retry_response.status_code, 200)
            self.assertEqual(retry_response.json()["status"], "queued")


if __name__ == "__main__":
    unittest.main()
