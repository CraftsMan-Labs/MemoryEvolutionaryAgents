from __future__ import annotations

import unittest

from memory_evolutionary_agents.phase2.handlers import (
    ChunkingService,
    EmbeddingService,
    NormalizationService,
)


class Phase2HandlersTestCase(unittest.TestCase):
    def test_normalization_service_returns_metadata(self) -> None:
        service = NormalizationService()
        output = service.normalize("/tmp/note.md", "line1\r\nline2\n")
        self.assertEqual(output.document_type, "markdown")
        self.assertEqual(output.document_text, "line1\nline2")
        self.assertEqual(output.metadata["source_extension"], "md")

    def test_chunking_service_creates_deterministic_chunks(self) -> None:
        chunking = ChunkingService(chunk_size=5)
        output = chunking.chunk("abcdefghij")
        self.assertEqual(len(output.chunks), 2)
        self.assertEqual(output.chunks[0].text, "abcde")
        self.assertEqual(output.chunks[1].text, "fghij")

    def test_embedding_service_emits_numeric_vectors(self) -> None:
        chunking = ChunkingService(chunk_size=4)
        chunks = chunking.chunk("abcdefgh")
        embeddings = EmbeddingService().embed(chunks)
        self.assertEqual(len(embeddings.embeddings), 2)
        self.assertGreater(len(embeddings.embeddings[0].vector), 0)


if __name__ == "__main__":
    unittest.main()
