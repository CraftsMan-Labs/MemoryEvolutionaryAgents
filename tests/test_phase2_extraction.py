from __future__ import annotations

import unittest

from memory_evolutionary_agents.phase2.contracts import (
    WorkflowExecutionResult,
    WorkflowStatus,
)
from memory_evolutionary_agents.phase2.errors import WorkflowExecutionError
from memory_evolutionary_agents.phase2.extraction_service import (
    WorkflowExtractionService,
)


class Phase2ExtractionServiceTestCase(unittest.TestCase):
    def test_extracts_structured_output_from_terminal_payload(self) -> None:
        service = WorkflowExtractionService()
        result = service.extract(
            WorkflowExecutionResult(
                status=WorkflowStatus.SUCCESS,
                raw_output={
                    "terminal_output": {
                        "project": "Q1 Platform Stabilization",
                        "problem": "High ingestion latency",
                        "solution": "Tune chunk size and retries",
                        "date": "2026-04-03",
                        "confidence": 0.91,
                        "tags": ["ingestion", "reliability"],
                        "entities": ["Qdrant", "Worker"],
                        "obsidian_note_path": "vault/memory-agent-summaries/project_status.md",
                        "qdrant_point_ids": ["chunk-1"],
                        "chunks": [
                            {
                                "chunk_id": "chunk-1",
                                "chunk_index": 0,
                                "text": "sample",
                                "start_offset": 0,
                                "end_offset": 6,
                            }
                        ],
                        "embeddings": [
                            {
                                "chunk_id": "chunk-1",
                                "vector": [0.1, 0.2],
                                "model_name": "deterministic-hash-embeddings-v1",
                            }
                        ],
                    }
                },
            )
        )
        self.assertEqual(result.project, "Q1 Platform Stabilization")
        self.assertEqual(result.tags, ["ingestion", "reliability"])
        self.assertEqual(result.qdrant_point_ids, ["chunk-1"])

    def test_fails_on_missing_terminal_or_nodes_payload(self) -> None:
        service = WorkflowExtractionService()
        with self.assertRaises(WorkflowExecutionError):
            service.extract(
                WorkflowExecutionResult(
                    status=WorkflowStatus.SUCCESS,
                    raw_output={"unexpected": {}},
                )
            )


if __name__ == "__main__":
    unittest.main()
