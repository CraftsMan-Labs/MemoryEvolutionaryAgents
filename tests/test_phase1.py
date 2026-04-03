from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any

from memory_evolutionary_agents.container import build_container
from memory_evolutionary_agents.contracts import (
    SourceCreateRequest,
    SourcePatchRequest,
    SourceState,
)
from memory_evolutionary_agents.scanner import ScanResult


class Phase1TestCase(unittest.TestCase):
    def test_source_create_and_scan_cycle(self) -> None:
        with _temp_env() as temp_dir:
            source_dir = _make_source_dir(temp_dir)
            file_path = source_dir / "sample.log"
            file_path.write_text("hello phase1", encoding="utf-8")

            container = build_container()
            source = container.source_registry.create_source(
                SourceCreateRequest(path=str(source_dir))
            )
            self.assertEqual(source.path, str(source_dir.resolve()))

            cycle = container.scheduler.run_cycle()
            self.assertGreaterEqual(cycle.discovered_count, 1)
            self.assertGreaterEqual(cycle.queued_count, 1)

            files = container.run_tracking.list_file_runs_for_run(cycle.run.id)
            self.assertGreaterEqual(len(files), 1)

    def test_dedup_marks_second_run_as_skipped(self) -> None:
        with _temp_env() as temp_dir:
            source_dir = _make_source_dir(temp_dir)
            file_path = source_dir / "stable.log"
            file_path.write_text("same-content", encoding="utf-8")

            container = build_container()
            container.source_registry.create_source(
                SourceCreateRequest(path=str(source_dir))
            )

            first = container.scheduler.run_cycle()
            second = container.scheduler.run_cycle()

            self.assertGreaterEqual(first.queued_count, 1)
            self.assertEqual(second.queued_count, 0)

    def test_source_pause_prevents_scanning(self) -> None:
        with _temp_env() as temp_dir:
            source_dir = _make_source_dir(temp_dir)
            file_path = source_dir / "ignored.log"
            file_path.write_text("ignored", encoding="utf-8")

            container = build_container()
            source = container.source_registry.create_source(
                SourceCreateRequest(path=str(source_dir))
            )
            container.source_registry.patch_source(
                source.id,
                SourcePatchRequest(state=SourceState.PAUSED),
            )

            cycle = container.scheduler.run_cycle()
            self.assertEqual(cycle.discovered_count, 0)

    def test_overlap_lock_rejects_parallel_cycle(self) -> None:
        with _temp_env() as temp_dir:
            source_dir = _make_source_dir(temp_dir)
            file_path = source_dir / "slow.log"
            file_path.write_text("slow", encoding="utf-8")

            container = build_container()
            container.source_registry.create_source(
                SourceCreateRequest(path=str(source_dir))
            )
            original_scanner = container.scheduler._scanner
            container.scheduler._scanner = _SlowScanner(
                original_scanner, delay_seconds=0.5
            )

            first_error: list[Exception] = []

            def _run_first() -> None:
                try:
                    container.scheduler.run_cycle()
                except Exception as exc:  # pragma: no cover
                    first_error.append(exc)

            thread = threading.Thread(target=_run_first)
            thread.start()
            time.sleep(0.1)

            with self.assertRaises(RuntimeError):
                container.scheduler.run_cycle()

            thread.join()
            self.assertEqual(len(first_error), 0)


class _SlowScanner:
    def __init__(self, base_scanner: Any, delay_seconds: float) -> None:
        self._base_scanner = base_scanner
        self._delay_seconds = delay_seconds

    def scan_source(self, source: Any) -> ScanResult:
        time.sleep(self._delay_seconds)
        return self._base_scanner.scan_source(source)


class _temp_env:
    def __enter__(self) -> str:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._old_db_path = _set_env(
            "MEA_DB_PATH", str(Path(self._temp_dir.name) / "phase1.db")
        )
        self._old_interval = _set_env("MEA_SCAN_INTERVAL_SECONDS", "300")
        self._old_timeout = _set_env("MEA_SCAN_CYCLE_TIMEOUT_SECONDS", "120")
        self._old_phase2_enabled = _set_env("MEA_PHASE2_ENABLED", "false")
        self._old_database_url = _set_env(
            "MEA_DATABASE_URL",
            "postgresql://memory_agents:memory_agents@localhost:5432/memory_agents",
        )
        return self._temp_dir.name

    def __exit__(self, *_: object) -> None:
        _set_env("MEA_DB_PATH", self._old_db_path)
        _set_env("MEA_SCAN_INTERVAL_SECONDS", self._old_interval)
        _set_env("MEA_SCAN_CYCLE_TIMEOUT_SECONDS", self._old_timeout)
        _set_env("MEA_PHASE2_ENABLED", self._old_phase2_enabled)
        _set_env("MEA_DATABASE_URL", self._old_database_url)
        self._temp_dir.cleanup()


def _set_env(key: str, value: str | None) -> str | None:
    current = os.getenv(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    return current


def _make_source_dir(temp_dir: str) -> Path:
    source_dir = Path(temp_dir) / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    return source_dir


if __name__ == "__main__":
    unittest.main()
