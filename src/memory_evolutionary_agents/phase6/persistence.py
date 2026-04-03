from __future__ import annotations

from datetime import datetime, timezone

from ..contracts import FileRunRecord
from ..database import Database
from .contracts import (
    FileProgressRecord,
    FileStage,
    FileTimelineEvent,
    RetryQueueRecord,
    RetryScheduleResult,
)


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class Phase6Repository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def latest_stage(self, file_run_id: int) -> FileStage | None:
        with self._database.connection() as conn:
            row = conn.execute(
                """
                SELECT to_stage
                FROM file_stage_events
                WHERE file_run_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (file_run_id,),
            ).fetchone()
        if row is None:
            return None
        return FileStage(str(row["to_stage"]))

    def latest_event_time(self, file_run_id: int) -> datetime | None:
        with self._database.connection() as conn:
            row = conn.execute(
                """
                SELECT recorded_at
                FROM file_stage_events
                WHERE file_run_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (file_run_id,),
            ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(str(row["recorded_at"]))

    def insert_stage_event(
        self,
        run_id: int,
        file_run_id: int,
        source_id: int,
        file_path: str,
        from_stage: FileStage | None,
        to_stage: FileStage,
        status: str,
        duration_ms: int | None,
        error_code: str | None,
        error_message: str | None,
        recorded_at: datetime,
    ) -> None:
        with self._database.connection() as conn:
            conn.execute(
                """
                INSERT INTO file_stage_events(
                  run_id,
                  file_run_id,
                  source_id,
                  file_path,
                  from_stage,
                  to_stage,
                  status,
                  duration_ms,
                  error_code,
                  error_message,
                  recorded_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    file_run_id,
                    source_id,
                    file_path,
                    None if from_stage is None else from_stage.value,
                    to_stage.value,
                    status,
                    duration_ms,
                    error_code,
                    error_message,
                    recorded_at.isoformat(),
                ),
            )

    def update_file_processing_row(
        self,
        file_run_id: int,
        stage: FileStage,
        status: str,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE file_processing_runs
                SET stage = ?, status = ?, error_code = ?, error_message = ?
                WHERE id = ?
                """,
                (stage.value, status, error_code, error_message, file_run_id),
            )

    def get_file_run(self, file_run_id: int) -> FileRunRecord | None:
        with self._database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM file_processing_runs WHERE id = ?",
                (file_run_id,),
            ).fetchone()
        if row is None:
            return None
        return FileRunRecord.model_validate(dict(row))

    def list_run_files(
        self,
        run_id: int,
        source_id: int | None,
        stage: FileStage | None,
        status: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
        limit: int,
    ) -> list[FileProgressRecord]:
        where = ["run_id = ?"]
        values: list[object] = [run_id]
        if source_id is not None:
            where.append("source_id = ?")
            values.append(source_id)
        if stage is not None:
            where.append("stage = ?")
            values.append(stage.value)
        if status is not None:
            where.append("status = ?")
            values.append(status)
        if from_date is not None:
            where.append("created_at >= ?")
            values.append(from_date.isoformat())
        if to_date is not None:
            where.append("created_at <= ?")
            values.append(to_date.isoformat())
        with self._database.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM file_processing_runs
                WHERE {" AND ".join(where)}
                ORDER BY id DESC
                LIMIT ?
                """,
                (*values, limit),
            ).fetchall()
        records: list[FileProgressRecord] = []
        for row in rows:
            records.append(
                FileProgressRecord(
                    file_run_id=int(row["id"]),
                    run_id=int(row["run_id"]),
                    source_id=int(row["source_id"]),
                    source_path=str(row["source_path"]),
                    file_path=str(row["file_path"]),
                    stage=FileStage(str(row["stage"])),
                    status=str(row["status"]),
                    error_code=None
                    if row["error_code"] is None
                    else str(row["error_code"]),
                    error_message=None
                    if row["error_message"] is None
                    else str(row["error_message"]),
                    created_at=datetime.fromisoformat(str(row["created_at"])),
                    updated_at=None,
                )
            )
        return records

    def list_timeline(self, file_run_id: int) -> list[FileTimelineEvent]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM file_stage_events
                WHERE file_run_id = ?
                ORDER BY id ASC
                """,
                (file_run_id,),
            ).fetchall()
        events: list[FileTimelineEvent] = []
        for row in rows:
            from_stage = None
            if row["from_stage"] is not None:
                from_stage = FileStage(str(row["from_stage"]))
            events.append(
                FileTimelineEvent(
                    id=int(row["id"]),
                    run_id=int(row["run_id"]),
                    file_run_id=int(row["file_run_id"]),
                    source_id=int(row["source_id"]),
                    file_path=str(row["file_path"]),
                    from_stage=from_stage,
                    to_stage=FileStage(str(row["to_stage"])),
                    status=str(row["status"]),
                    duration_ms=None
                    if row["duration_ms"] is None
                    else int(row["duration_ms"]),
                    error_code=None
                    if row["error_code"] is None
                    else str(row["error_code"]),
                    error_message=None
                    if row["error_message"] is None
                    else str(row["error_message"]),
                    recorded_at=datetime.fromisoformat(str(row["recorded_at"])),
                )
            )
        return events

    def upsert_retry_queue(
        self,
        file_run_id: int,
        run_id: int,
        source_id: int,
        file_path: str,
        status: str,
        attempt_count: int,
        max_attempts: int,
        next_attempt_at: datetime,
        last_error_code: str | None,
        last_error_message: str | None,
    ) -> RetryScheduleResult:
        now = _utc_now()
        with self._database.connection() as conn:
            existing = conn.execute(
                "SELECT id FROM file_retry_queue WHERE file_run_id = ?",
                (file_run_id,),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO file_retry_queue(
                      file_run_id,
                      run_id,
                      source_id,
                      file_path,
                      status,
                      attempt_count,
                      max_attempts,
                      next_attempt_at,
                      last_error_code,
                      last_error_message,
                      created_at,
                      updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_run_id,
                        run_id,
                        source_id,
                        file_path,
                        status,
                        attempt_count,
                        max_attempts,
                        next_attempt_at.isoformat(),
                        last_error_code,
                        last_error_message,
                        now,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE file_retry_queue
                    SET status = ?, attempt_count = ?, max_attempts = ?, next_attempt_at = ?,
                        last_error_code = ?, last_error_message = ?, updated_at = ?
                    WHERE file_run_id = ?
                    """,
                    (
                        status,
                        attempt_count,
                        max_attempts,
                        next_attempt_at.isoformat(),
                        last_error_code,
                        last_error_message,
                        now,
                        file_run_id,
                    ),
                )
        return RetryScheduleResult(
            file_run_id=file_run_id,
            attempt_count=attempt_count,
            next_attempt_at=next_attempt_at,
            status=status,
        )

    def get_retry_item(self, file_run_id: int) -> RetryQueueRecord | None:
        with self._database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM file_retry_queue WHERE file_run_id = ?",
                (file_run_id,),
            ).fetchone()
        if row is None:
            return None
        return RetryQueueRecord.model_validate(dict(row))

    def list_due_retries(self, now: datetime, limit: int) -> list[RetryQueueRecord]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM file_retry_queue
                WHERE status = 'queued' AND next_attempt_at <= ?
                ORDER BY next_attempt_at ASC
                LIMIT ?
                """,
                (now.isoformat(), limit),
            ).fetchall()
        return [RetryQueueRecord.model_validate(dict(row)) for row in rows]

    def mark_retry_in_progress(self, file_run_id: int) -> None:
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE file_retry_queue
                SET status = 'in_progress', updated_at = ?
                WHERE file_run_id = ?
                """,
                (_utc_now(), file_run_id),
            )

    def mark_retry_done(self, file_run_id: int, status: str) -> None:
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE file_retry_queue
                SET status = ?, updated_at = ?
                WHERE file_run_id = ?
                """,
                (status, _utc_now(), file_run_id),
            )

    def dead_letter_items(self, limit: int = 100) -> list[RetryQueueRecord]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM file_retry_queue
                WHERE status = 'poisoned'
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [RetryQueueRecord.model_validate(dict(row)) for row in rows]
