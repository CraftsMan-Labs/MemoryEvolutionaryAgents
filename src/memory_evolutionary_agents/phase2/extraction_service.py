from __future__ import annotations

from .contracts import (
    ChunkRecord,
    EmbeddingRecord,
    StructuredMemoryResult,
    WorkflowExecutionResult,
)
from .errors import WorkflowExecutionError


class WorkflowExtractionService:
    def extract(
        self, execution_result: WorkflowExecutionResult
    ) -> StructuredMemoryResult:
        raw = execution_result.raw_output
        terminal = raw.get("terminal_output")
        nodes = raw.get("nodes")
        if isinstance(terminal, dict):
            return self._from_terminal(terminal)
        if isinstance(nodes, dict):
            return self._from_nodes(nodes)
        raise WorkflowExecutionError(
            "workflow output missing terminal_output and nodes"
        )

    def _from_terminal(self, terminal: dict[str, object]) -> StructuredMemoryResult:
        return StructuredMemoryResult(
            project=_optional_str(terminal.get("project")),
            problem=_optional_str(terminal.get("problem")),
            solution=_optional_str(terminal.get("solution")),
            date=_optional_str(terminal.get("date")),
            confidence=_optional_float(terminal.get("confidence"), default=0.0),
            tags=_string_list(terminal.get("tags")),
            entities=_string_list(terminal.get("entities")),
            obsidian_note_path=_optional_str(terminal.get("obsidian_note_path")),
            qdrant_point_ids=_string_list(terminal.get("qdrant_point_ids")),
            chunks=_chunk_list(terminal.get("chunks")),
            embeddings=_embedding_list(terminal.get("embeddings")),
        )

    def _from_nodes(self, nodes: dict[str, object]) -> StructuredMemoryResult:
        extraction_output = _node_output(nodes, "extract_structured_memory")
        classification_output = _node_output(nodes, "classify_memory")
        chunk_output = _node_output(nodes, "chunk_document")
        embedding_output = _node_output(nodes, "embed_chunks")
        qdrant_output = _node_output(nodes, "upsert_qdrant")
        obsidian_output = _node_output(nodes, "write_obsidian_summary")

        return StructuredMemoryResult(
            project=_optional_str(extraction_output.get("project")),
            problem=_optional_str(extraction_output.get("problem")),
            solution=_optional_str(extraction_output.get("solution")),
            date=_optional_str(extraction_output.get("date")),
            confidence=_optional_float(
                extraction_output.get("confidence"), default=0.0
            ),
            tags=_string_list(classification_output.get("tags")),
            entities=_string_list(classification_output.get("entities")),
            obsidian_note_path=_optional_str(obsidian_output.get("obsidian_note_path")),
            qdrant_point_ids=_string_list(qdrant_output.get("qdrant_point_ids")),
            chunks=_chunk_list(chunk_output.get("chunks")),
            embeddings=_embedding_list(embedding_output.get("embeddings")),
        )


def _node_output(nodes: dict[str, object], node_id: str) -> dict[str, object]:
    node = nodes.get(node_id)
    if isinstance(node, dict) is False:
        raise WorkflowExecutionError(f"workflow output missing node: {node_id}")
    output = node.get("output")
    if isinstance(output, dict) is False:
        raise WorkflowExecutionError(f"workflow node missing output: {node_id}")
    return output


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise WorkflowExecutionError("expected string or null in workflow output")


def _optional_float(value: object, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    raise WorkflowExecutionError("expected numeric value in workflow output")


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list) is False:
        raise WorkflowExecutionError("expected list of strings in workflow output")
    result: list[str] = []
    for item in value:
        if isinstance(item, str) is False:
            raise WorkflowExecutionError("expected list of strings in workflow output")
        result.append(item)
    return result


def _chunk_list(value: object) -> list[ChunkRecord]:
    if value is None:
        return []
    if isinstance(value, list) is False:
        raise WorkflowExecutionError("expected list of chunks in workflow output")
    chunks: list[ChunkRecord] = []
    for item in value:
        if isinstance(item, dict) is False:
            raise WorkflowExecutionError("expected chunk object in workflow output")
        chunks.append(ChunkRecord.model_validate(item))
    return chunks


def _embedding_list(value: object) -> list[EmbeddingRecord]:
    if value is None:
        return []
    if isinstance(value, list) is False:
        raise WorkflowExecutionError("expected list of embeddings in workflow output")
    records: list[EmbeddingRecord] = []
    for item in value:
        if isinstance(item, dict) is False:
            raise WorkflowExecutionError("expected embedding object in workflow output")
        records.append(EmbeddingRecord.model_validate(item))
    return records
