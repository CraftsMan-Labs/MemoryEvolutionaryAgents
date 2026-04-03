from __future__ import annotations

import unittest

from memory_evolutionary_agents.phase2.handlers import (
    ChunkingService,
    EmbeddingService,
    NormalizationService,
)
from memory_evolutionary_agents.phase2.workflow_handlers import (
    chunk_document,
    emit_telemetry,
    normalize_file,
    write_obsidian_summary,
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

    def test_workflow_normalize_uses_context_when_payload_has_topic_values(
        self,
    ) -> None:
        result = normalize_file(
            file_path="phase2.normalize",
            payload={
                "file_path": "{{ input.file_path }}",
                "file_content": "{{ input.file_content }}",
            },
            context={
                "input": {
                    "file_path": "/tmp/incident.md",
                    "file_content": "Project Orion\nProblem deadlock\nSolution ordered locks",
                }
            },
        )
        self.assertIn("Project Orion", result["document_text"])
        self.assertEqual(result["document_type"], "markdown")

    def test_workflow_chunk_document_ignores_topic_literal(self) -> None:
        result = chunk_document(
            document_text="phase2.chunk",
            payload={
                "document_text": "{{ nodes.normalize_file.output.document_text }}"
            },
            context={
                "outputs": {
                    "normalize_file": {
                        "output": {
                            "document_text": "alpha beta gamma",
                        }
                    }
                }
            },
        )
        self.assertGreater(len(result["chunks"]), 0)
        self.assertEqual(result["chunks"][0]["text"], "alpha beta gamma")

    def test_workflow_summary_resolves_values_from_context_outputs(self) -> None:
        result = write_obsidian_summary(
            project="phase2.obsidian",
            problem="{{ nodes.extract_structured_memory.output.problem }}",
            solution="{{ nodes.extract_structured_memory.output.solution }}",
            file_path="{{ input.file_path }}",
            payload={"file_path": "{{ input.file_path }}"},
            context={
                "input": {"file_path": "/tmp/incident.md"},
                "outputs": {
                    "extract_structured_memory": {
                        "output": {
                            "project": "Incident Review",
                            "problem": "race condition",
                            "solution": "ordered lock acquisition",
                        }
                    }
                },
            },
        )
        self.assertEqual(result["title"], "Incident Review")
        self.assertIn("race condition", result["summary"])
        self.assertEqual(
            result["obsidian_note_path"], "memory-agent-summaries/incident.md"
        )

    def test_workflow_telemetry_uses_input_correlation_when_template_unresolved(
        self,
    ) -> None:
        result = emit_telemetry(
            correlation_id="{{ input.correlation_id }}",
            payload={"correlation_id": "phase2.telemetry", "status": "success"},
            context={"input": {"correlation_id": "run-1-file-1"}},
        )
        self.assertEqual(result["correlation_id"], "run-1-file-1")
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
