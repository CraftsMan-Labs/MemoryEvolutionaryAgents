from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..run_tracking import RunTrackingService
from .contracts import (
    FileRetryRequest,
    FileStage,
    FileStageSummary,
    FileStatusSummary,
    FileTimelineResponse,
    RetryQueueRecord,
    RetryScheduleResult,
    RetryScheduleResult,
    RunFilesQuery,
    RunFilesResponse,
    StageTransitionRequest,
)
from .errors import FileRunNotFoundError, RetryNotAllowedError
from .persistence import Phase6Repository
from .policy import StageTransitionPolicyService


@dataclass(frozen=True)
class RetryBackoffConfig:
    base_seconds: int = 30
    max_seconds: int = 900
    max_attempts: int = 5


class ProgressEventPublisher:
    def __init__(self) -> None:
        self._subscribers: dict[int, list[asyncio.Queue[str]]] = defaultdict(list)

    def publish(self, run_id: int, payload: dict[str, object]) -> None:
        text = json.dumps(payload)
        queues = self._subscribers.get(run_id, [])
        for queue in queues:
            queue.put_nowait(text)

    def subscribe(self, run_id: int) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._subscribers[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: int, queue: asyncio.Queue[str]) -> None:
        queues = self._subscribers.get(run_id, [])
        if queue in queues:
            queues.remove(queue)
        if len(queues) == 0 and run_id in self._subscribers:
            del self._subscribers[run_id]


class FileProgressService:
    def __init__(
        self,
        run_tracking: RunTrackingService,
        repository: Phase6Repository,
        transition_policy: StageTransitionPolicyService,
        retry_config: RetryBackoffConfig,
        publisher: ProgressEventPublisher,
    ) -> None:
        self._run_tracking = run_tracking
        self._repository = repository
        self._transition_policy = transition_policy
        self._retry_config = retry_config
        self._publisher = publisher

    def transition(self, request: StageTransitionRequest) -> None:
        previous = self._repository.latest_stage(request.file_run_id)
        self._transition_policy.assert_transition(previous, request.to_stage)
        duration_ms = self._compute_duration_ms(
            file_run_id=request.file_run_id,
            occurred_at=request.occurred_at,
        )
        self._repository.insert_stage_event(
            run_id=request.run_id,
            file_run_id=request.file_run_id,
            source_id=request.source_id,
            file_path=request.file_path,
            from_stage=previous,
            to_stage=request.to_stage,
            status=request.status,
            duration_ms=duration_ms,
            error_code=request.error_code,
            error_message=request.error_message,
            recorded_at=request.occurred_at,
        )
        self._repository.update_file_processing_row(
            file_run_id=request.file_run_id,
            stage=request.to_stage,
            status=request.status,
            error_code=request.error_code,
            error_message=request.error_message,
        )
        self._publisher.publish(
            request.run_id,
            {
                "type": "stage_event",
                "file_run_id": request.file_run_id,
                "stage": request.to_stage.value,
                "status": request.status,
                "error_code": request.error_code,
                "error_message": request.error_message,
                "recorded_at": request.occurred_at.isoformat(),
            },
        )

    def list_run_files(self, run_id: int, query: RunFilesQuery) -> RunFilesResponse:
        files = self._repository.list_run_files(
            run_id=run_id,
            source_id=query.source_id,
            stage=query.stage,
            status=query.status,
            from_date=query.from_date,
            to_date=query.to_date,
            limit=query.limit,
        )
        stage_counts: dict[FileStage, int] = defaultdict(int)
        status_counts: dict[str, int] = defaultdict(int)
        for row in files:
            stage_counts[row.stage] += 1
            status_counts[row.status] += 1
        stage_summary = [
            FileStageSummary(stage=stage, total=total)
            for stage, total in sorted(
                stage_counts.items(),
                key=lambda item: item[0].value,
            )
        ]
        status_summary = [
            FileStatusSummary(status=status, total=total)
            for status, total in sorted(status_counts.items(), key=lambda item: item[0])
        ]
        return RunFilesResponse(
            run_id=run_id,
            files=files,
            stage_summary=stage_summary,
            status_summary=status_summary,
        )

    def timeline(self, file_run_id: int) -> FileTimelineResponse:
        file_row = self._repository.get_file_run(file_run_id)
        if file_row is None:
            raise FileRunNotFoundError(f"file run {file_run_id} was not found")
        return FileTimelineResponse(
            file_run_id=file_run_id,
            events=self._repository.list_timeline(file_run_id),
        )

    def queue_retry(
        self,
        file_run_id: int,
        error_code: str | None,
        error_message: str | None,
    ) -> RetryScheduleResult:
        file_row = self._repository.get_file_run(file_run_id)
        if file_row is None:
            raise FileRunNotFoundError(f"file run {file_run_id} was not found")
        existing_retry = self._repository.get_retry_item(file_run_id)
        attempts = 0 if existing_retry is None else existing_retry.attempt_count
        next_attempt = self._next_attempt_at(attempts + 1)
        status = "queued"
        if attempts + 1 >= self._retry_config.max_attempts:
            status = "poisoned"
        result = self._repository.upsert_retry_queue(
            file_run_id=file_run_id,
            run_id=file_row.run_id,
            source_id=file_row.source_id,
            file_path=file_row.file_path,
            status=status,
            attempt_count=attempts + 1,
            max_attempts=self._retry_config.max_attempts,
            next_attempt_at=next_attempt,
            last_error_code=error_code,
            last_error_message=error_message,
        )
        if status == "poisoned":
            self.transition(
                StageTransitionRequest(
                    run_id=file_row.run_id,
                    file_run_id=file_run_id,
                    source_id=file_row.source_id,
                    file_path=file_row.file_path,
                    to_stage=FileStage.POISONED,
                    status="failed",
                    error_code=error_code,
                    error_message=error_message,
                    occurred_at=datetime.now(tz=timezone.utc),
                )
            )
            return result
        self.transition(
            StageTransitionRequest(
                run_id=file_row.run_id,
                file_run_id=file_run_id,
                source_id=file_row.source_id,
                file_path=file_row.file_path,
                to_stage=FileStage.RETRY_QUEUED,
                status="queued",
                error_code=error_code,
                error_message=error_message,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )
        return result

    def manual_retry(
        self, file_run_id: int, request: FileRetryRequest
    ) -> RetryScheduleResult:
        _ = request
        file_row = self._repository.get_file_run(file_run_id)
        if file_row is None:
            raise FileRunNotFoundError(f"file run {file_run_id} was not found")
        if file_row.stage == FileStage.COMPLETED.value:
            raise RetryNotAllowedError("completed file cannot be retried")
        return self.queue_retry(
            file_run_id=file_run_id,
            error_code="manual_retry",
            error_message="manual retry requested",
        )

    def next_due_retries(self, limit: int = 100) -> list[RetryQueueRecord]:
        return self._repository.list_due_retries(datetime.now(tz=timezone.utc), limit)

    def begin_retry(self, item: RetryQueueRecord) -> None:
        self._repository.mark_retry_in_progress(item.file_run_id)
        self.transition(
            StageTransitionRequest(
                run_id=item.run_id,
                file_run_id=item.file_run_id,
                source_id=item.source_id,
                file_path=item.file_path,
                to_stage=FileStage.RETRYING,
                status="running",
                error_code=None,
                error_message=None,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def complete_retry(self, item: RetryQueueRecord) -> None:
        self._repository.mark_retry_done(item.file_run_id, "done")

    def fail_retry(self, item: RetryQueueRecord, exc: Exception) -> None:
        self._repository.mark_retry_done(item.file_run_id, "failed")
        self.queue_retry(
            file_run_id=item.file_run_id,
            error_code="retry_failed",
            error_message=str(exc),
        )

    def dead_letter_items(self, limit: int = 100) -> list[RetryQueueRecord]:
        return self._repository.dead_letter_items(limit)

    def subscribe(self, run_id: int) -> asyncio.Queue[str]:
        return self._publisher.subscribe(run_id)

    def unsubscribe(self, run_id: int, queue: asyncio.Queue[str]) -> None:
        self._publisher.unsubscribe(run_id, queue)

    def _compute_duration_ms(
        self, file_run_id: int, occurred_at: datetime
    ) -> int | None:
        latest = self._repository.latest_event_time(file_run_id)
        if latest is None:
            return None
        duration_seconds = (occurred_at - latest).total_seconds()
        if duration_seconds < 0:
            return 0
        return int(duration_seconds * 1000)

    def _next_attempt_at(self, attempt: int) -> datetime:
        bounded_attempt = max(1, attempt)
        backoff_seconds = self._retry_config.base_seconds * (2 ** (bounded_attempt - 1))
        backoff_seconds = min(backoff_seconds, self._retry_config.max_seconds)
        return datetime.now(tz=timezone.utc) + timedelta(seconds=backoff_seconds)
