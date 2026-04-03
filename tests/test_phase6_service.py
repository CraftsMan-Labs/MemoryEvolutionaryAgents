from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from memory_evolutionary_agents.contracts import FileSnapshot
from memory_evolutionary_agents.database import Database
from memory_evolutionary_agents.phase6.contracts import (
    FileStage,
    StageTransitionRequest,
)
from memory_evolutionary_agents.phase6.persistence import Phase6Repository
from memory_evolutionary_agents.phase6.policy import StageTransitionPolicyService
from memory_evolutionary_agents.phase6.service import (
    FileProgressService,
    ProgressEventPublisher,
    RetryBackoffConfig,
)
from memory_evolutionary_agents.repositories import RunRepository, SourceRepository
from memory_evolutionary_agents.run_tracking import RunTrackingService


class Phase6ServiceTestCase(unittest.TestCase):
    def test_stage_timeline_and_retry_poisoning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "phase6.db")
            database = Database(db_path)
            database.initialize()
            source_repository = SourceRepository(database)
            run_repository = RunRepository(database)
            source = source_repository.create(str(Path(temp_dir).resolve()))
            run = run_repository.start_run()
            run_repository.upsert_file_discovery(
                run_id=run.id,
                snapshot=FileSnapshot(
                    source_id=source.id,
                    source_path=source.path,
                    file_path="/tmp/a.md",
                    mtime_ns=1,
                    content_hash="abc",
                    fingerprint="f-1",
                ),
            )
            file_row = run_repository.list_file_runs_for_run(run.id)[0]

            service = FileProgressService(
                run_tracking=RunTrackingService(database),
                repository=Phase6Repository(database),
                transition_policy=StageTransitionPolicyService(),
                retry_config=RetryBackoffConfig(
                    base_seconds=1,
                    max_seconds=4,
                    max_attempts=3,
                ),
                publisher=ProgressEventPublisher(),
            )

            service.transition(
                StageTransitionRequest(
                    run_id=run.id,
                    file_run_id=file_row.id,
                    source_id=source.id,
                    file_path=file_row.file_path,
                    to_stage=FileStage.WORKFLOW_STARTED,
                    status="running",
                    error_code=None,
                    error_message=None,
                    occurred_at=datetime.now(tz=timezone.utc),
                )
            )
            service.transition(
                StageTransitionRequest(
                    run_id=run.id,
                    file_run_id=file_row.id,
                    source_id=source.id,
                    file_path=file_row.file_path,
                    to_stage=FileStage.FAILED,
                    status="failed",
                    error_code="workflow_failed",
                    error_message="boom",
                    occurred_at=datetime.now(tz=timezone.utc),
                )
            )

            first = service.queue_retry(file_row.id, "workflow_failed", "boom")
            second = service.queue_retry(file_row.id, "workflow_failed", "boom")
            third = service.queue_retry(file_row.id, "workflow_failed", "boom")

            self.assertEqual(first.status, "queued")
            self.assertEqual(second.status, "queued")
            self.assertEqual(third.status, "poisoned")
            self.assertGreaterEqual(second.next_attempt_at, first.next_attempt_at)

            timeline = service.timeline(file_row.id)
            self.assertGreaterEqual(len(timeline.events), 4)

            dead_letter = service.dead_letter_items()
            self.assertEqual(len(dead_letter), 1)
            self.assertEqual(dead_letter[0].file_run_id, file_row.id)

    def test_settle_retry_marks_terminal_retry_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "phase6-settle.db")
            database = Database(db_path)
            database.initialize()
            source_repository = SourceRepository(database)
            run_repository = RunRepository(database)
            source = source_repository.create(str(Path(temp_dir).resolve()))
            run = run_repository.start_run()
            run_repository.upsert_file_discovery(
                run_id=run.id,
                snapshot=FileSnapshot(
                    source_id=source.id,
                    source_path=source.path,
                    file_path="/tmp/b.md",
                    mtime_ns=1,
                    content_hash="def",
                    fingerprint="f-2",
                ),
            )
            file_row = run_repository.list_file_runs_for_run(run.id)[0]

            repository = Phase6Repository(database)
            service = FileProgressService(
                run_tracking=RunTrackingService(database),
                repository=repository,
                transition_policy=StageTransitionPolicyService(),
                retry_config=RetryBackoffConfig(
                    base_seconds=1,
                    max_seconds=4,
                    max_attempts=3,
                ),
                publisher=ProgressEventPublisher(),
            )

            repository.upsert_retry_queue(
                file_run_id=file_row.id,
                run_id=run.id,
                source_id=source.id,
                file_path=file_row.file_path,
                status="in_progress",
                attempt_count=1,
                max_attempts=3,
                next_attempt_at=datetime.now(tz=timezone.utc),
                last_error_code="workflow_failed",
                last_error_message="boom",
            )

            service.settle_retry(file_row.id, FileStage.POISONED.value)
            retry_item = repository.get_retry_item(file_row.id)

            self.assertIsNotNone(retry_item)
            if retry_item is None:
                self.fail("retry item should exist")
            self.assertEqual(retry_item.status, "poisoned")


if __name__ == "__main__":
    unittest.main()
