from __future__ import annotations

from .contracts import FileRunRecord, FileSnapshot, IngestionRunRecord
from .database import Database
from .repositories import RunRepository


class RunTrackingService:
    def __init__(self, database: Database) -> None:
        self._repository = RunRepository(database)

    def start_run(self) -> IngestionRunRecord:
        return self._repository.start_run()

    def finish_run(
        self, run_id: int, total_discovered: int, total_queued: int, total_failed: int
    ) -> IngestionRunRecord:
        return self._repository.finish_run(
            run_id=run_id,
            discovered=total_discovered,
            queued=total_queued,
            failed=total_failed,
        )

    def get_run(self, run_id: int) -> IngestionRunRecord:
        return self._repository.get_run(run_id)

    def list_runs(self, limit: int = 20) -> list[IngestionRunRecord]:
        return self._repository.list_runs(limit)

    def mark_file_discovered(self, run_id: int, snapshot: FileSnapshot) -> None:
        self._repository.upsert_file_discovery(run_id, snapshot)

    def mark_source_scan_error(
        self,
        run_id: int,
        source_id: int,
        source_path: str,
        error_code: str,
        error_message: str,
    ) -> None:
        self._repository.mark_scan_error(
            run_id=run_id,
            source_id=source_id,
            source_path=source_path,
            error_code=error_code,
            error_message=error_message,
        )

    def list_file_runs_for_run(self, run_id: int) -> list[FileRunRecord]:
        return self._repository.list_file_runs_for_run(run_id)
