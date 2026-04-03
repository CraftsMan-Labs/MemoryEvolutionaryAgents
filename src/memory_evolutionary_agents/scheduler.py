from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from time import monotonic

from .contracts import IngestionRunRecord
from .run_tracking import RunTrackingService
from .scanner import IncrementalScanner
from .source_registry import SourceRegistryService


@dataclass(frozen=True)
class ScanCycleResult:
    run: IngestionRunRecord
    discovered_count: int
    queued_count: int
    failed_count: int


class CronIngestionScheduler:
    def __init__(
        self,
        source_registry: SourceRegistryService,
        run_tracking: RunTrackingService,
        scanner: IncrementalScanner,
        interval_seconds: int,
        cycle_timeout_seconds: int,
    ) -> None:
        self._source_registry = source_registry
        self._run_tracking = run_tracking
        self._scanner = scanner
        self._interval_seconds = interval_seconds
        self._cycle_timeout_seconds = cycle_timeout_seconds
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()

    def run_cycle(self) -> ScanCycleResult:
        acquired = self._lock.acquire(blocking=False)
        if acquired is False:
            raise RuntimeError("ingestion cycle already running")
        try:
            started_run = self._run_tracking.start_run()
            discovered_count = 0
            queued_count = 0
            failed_count = 0
            deadline = monotonic() + self._cycle_timeout_seconds

            for source in self._source_registry.list_active_sources():
                if self._cancel_event.is_set():
                    break
                if monotonic() >= deadline:
                    failed_count += 1
                    self._run_tracking.mark_source_scan_error(
                        started_run.id,
                        source.id,
                        source.path,
                        "scan_timeout",
                        "scan cycle timeout reached before source scan",
                    )
                    self._source_registry.set_scan_status(
                        source.id,
                        "scan cycle timeout reached",
                        scanned_files=0,
                        scan_errors=1,
                    )
                    continue

                scan_result = self._scanner.scan_source(source)
                source_error: str | None = None
                source_error_count = 0

                for snapshot in scan_result.snapshots:
                    self._run_tracking.mark_file_discovered(started_run.id, snapshot)
                    discovered_count += 1
                for error in scan_result.errors:
                    self._run_tracking.mark_source_scan_error(
                        started_run.id,
                        source.id,
                        source.path,
                        "scan_file_error",
                        error,
                    )
                    failed_count += 1
                    source_error_count += 1
                    source_error = error

                self._source_registry.set_scan_status(
                    source.id,
                    source_error,
                    scanned_files=len(scan_result.snapshots),
                    scan_errors=source_error_count,
                )

            file_rows = self._run_tracking.list_file_runs_for_run(started_run.id)
            for file_row in file_rows:
                if file_row.status == "queued":
                    queued_count += 1

            completed_run = self._run_tracking.finish_run(
                run_id=started_run.id,
                total_discovered=discovered_count,
                total_queued=queued_count,
                total_failed=failed_count,
            )

            return ScanCycleResult(
                run=completed_run,
                discovered_count=discovered_count,
                queued_count=queued_count,
                failed_count=failed_count,
            )
        finally:
            self._lock.release()

    def run_forever(self) -> None:
        self._cancel_event.clear()
        while self._cancel_event.is_set() is False:
            self.run_cycle()
            time.sleep(self._interval_seconds)

    def request_stop(self) -> None:
        self._cancel_event.set()
