from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from memory_evolutionary_agents.phase2.adapters import (
    FileSystemObsidianAdapter,
    _to_qdrant_point_id,
)
from memory_evolutionary_agents.phase2.contracts import ObsidianWriteRequest


class Phase2AdaptersTestCase(unittest.TestCase):
    def test_non_uuid_string_point_ids_are_hashed_to_positive_int(self) -> None:
        point_id = _to_qdrant_point_id("chunk-integration-1")
        self.assertIsInstance(point_id, int)
        if isinstance(point_id, int):
            self.assertGreater(point_id, 0)

    def test_uuid_point_id_is_preserved(self) -> None:
        raw = "123e4567-e89b-12d3-a456-426614174000"
        self.assertEqual(_to_qdrant_point_id(raw), raw)

    def test_obsidian_summary_path_does_not_append_md_twice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = FileSystemObsidianAdapter(temp_dir)
            response = adapter.write_summary(
                ObsidianWriteRequest(
                    source_path=temp_dir,
                    file_path="/tmp/incidents/postmortem.md",
                    title="Incident",
                    body="Problem: race\nSolution: lock ordering",
                )
            )
            self.assertTrue(
                response.note_path.endswith("memory-agent-summaries/postmortem.md")
            )
            self.assertTrue(Path(response.note_path).exists())


if __name__ == "__main__":
    unittest.main()
