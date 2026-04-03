from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from memory_evolutionary_agents.contracts import SourceRecord, SourceState
from memory_evolutionary_agents.scanner import IncrementalScanner


class ScannerTestCase(unittest.TestCase):
    def test_scan_source_ignores_hidden_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            included = root / "notes" / "project.md"
            included.parent.mkdir(parents=True, exist_ok=True)
            included.write_text("visible", encoding="utf-8")

            hidden_dir_file = root / ".obsidian" / "workspace.json"
            hidden_dir_file.parent.mkdir(parents=True, exist_ok=True)
            hidden_dir_file.write_text("{}", encoding="utf-8")

            hidden_file = root / ".env"
            hidden_file.write_text("SECRET=1", encoding="utf-8")

            scanner = IncrementalScanner()
            source = SourceRecord(
                id=1,
                path=str(root),
                state=SourceState.ACTIVE,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                last_scan_at=None,
                last_error=None,
                last_scan_file_count=0,
                last_scan_error_count=0,
            )

            result = scanner.scan_source(source)

            scanned_paths = {Path(snapshot.file_path) for snapshot in result.snapshots}
            self.assertEqual(scanned_paths, {included.resolve()})
            self.assertEqual(result.errors, [])

    def test_scan_source_ignores_generated_and_dependency_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            included = root / "src" / "project.md"
            included.parent.mkdir(parents=True, exist_ok=True)
            included.write_text("visible", encoding="utf-8")

            generated = root / "memory-agent-summaries" / "project.md"
            generated.parent.mkdir(parents=True, exist_ok=True)
            generated.write_text("generated", encoding="utf-8")

            dependency = root / "node_modules" / "pkg" / "index.js"
            dependency.parent.mkdir(parents=True, exist_ok=True)
            dependency.write_text("module", encoding="utf-8")

            scanner = IncrementalScanner()
            source = SourceRecord(
                id=1,
                path=str(root),
                state=SourceState.ACTIVE,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                last_scan_at=None,
                last_error=None,
                last_scan_file_count=0,
                last_scan_error_count=0,
            )

            result = scanner.scan_source(source)
            scanned_paths = {Path(snapshot.file_path) for snapshot in result.snapshots}
            self.assertEqual(scanned_paths, {included.resolve()})
            self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
