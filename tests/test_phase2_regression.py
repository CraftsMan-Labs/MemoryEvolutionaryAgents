from __future__ import annotations

from pathlib import Path
import unittest

from memory_evolutionary_agents.phase2.handlers import (
    ChunkingService,
    NormalizationService,
)


class Phase2RegressionFixtureTestCase(unittest.TestCase):
    def test_fixture_files_are_normalized_and_chunked(self) -> None:
        fixtures_root = Path(__file__).resolve().parent / "fixtures" / "phase2"
        fixture_files = list(fixtures_root.glob("**/*.*"))
        self.assertGreaterEqual(len(fixture_files), 2)

        normalizer = NormalizationService()
        chunker = ChunkingService(chunk_size=80)

        for file_path in fixture_files:
            content = file_path.read_text(encoding="utf-8")
            normalized = normalizer.normalize(str(file_path), content)
            chunks = chunker.chunk(normalized.document_text)
            self.assertGreaterEqual(len(normalized.document_text), 1)
            self.assertGreaterEqual(len(chunks.chunks), 1)

    def test_empty_document_path_triggers_empty_chunk_output(self) -> None:
        chunker = ChunkingService(chunk_size=40)
        chunks = chunker.chunk("")
        self.assertEqual(len(chunks.chunks), 0)


if __name__ == "__main__":
    unittest.main()
