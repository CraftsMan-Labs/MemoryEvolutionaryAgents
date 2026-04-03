from __future__ import annotations

import unittest

from pydantic import ValidationError

from memory_evolutionary_agents.phase2.contracts import (
    CanonicalMemoryPersistRequest,
    IngestWorkflowInput,
)


class Phase2ContractsTestCase(unittest.TestCase):
    def test_ingest_workflow_input_requires_explicit_fields(self) -> None:
        request = IngestWorkflowInput(
            run_id=10,
            file_run_id=11,
            source_id=12,
            source_path="/vault",
            file_path="/vault/note.md",
            file_content="hello",
            correlation_id="run-10-file-11",
        )
        self.assertEqual(request.run_id, 10)
        self.assertEqual(request.file_run_id, 11)

    def test_canonical_memory_confidence_is_bounded(self) -> None:
        with self.assertRaises(ValidationError):
            CanonicalMemoryPersistRequest(
                source_id=1,
                source_path="/vault",
                file_path="/vault/a.md",
                content_hash="hash",
                project=None,
                problem=None,
                solution=None,
                event_date=None,
                extraction_confidence=1.4,
                tags=[],
                entities=[],
                obsidian_note_path=None,
                qdrant_point_ids=[],
                ontology_terms=[],
                taxonomy_tags=[],
                relation_edges=[],
            )


if __name__ == "__main__":
    unittest.main()
