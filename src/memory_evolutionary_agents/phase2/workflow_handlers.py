from __future__ import annotations

from typing import Any

from .contracts import ChunkRecord, ChunkingOutput
from .handlers import ChunkingService, EmbeddingService, NormalizationService

_NORMALIZATION_SERVICE = NormalizationService()
_CHUNKING_SERVICE = ChunkingService()
_EMBEDDING_SERVICE = EmbeddingService()


def normalize_file(
    file_path: str, *, file_content: str, context: dict[str, Any]
) -> dict[str, Any]:
    _ = context
    normalized = _NORMALIZATION_SERVICE.normalize(
        file_path=file_path, file_content=file_content
    )
    return {
        "document_text": normalized.document_text,
        "document_type": normalized.document_type,
        "metadata": normalized.metadata,
    }


def chunk_document(document_text: str, *, context: dict[str, Any]) -> dict[str, Any]:
    _ = context
    chunks = _CHUNKING_SERVICE.chunk(document_text)
    return {
        "chunks": [chunk.model_dump() for chunk in chunks.chunks],
    }


def embed_chunks(
    chunks: list[dict[str, Any]], *, context: dict[str, Any]
) -> dict[str, Any]:
    _ = context
    chunk_models: list[ChunkRecord] = []
    for index, raw in enumerate(chunks):
        text_value = raw.get("text")
        text = text_value if isinstance(text_value, str) else ""
        chunk_id_value = raw.get("chunk_id")
        chunk_id = (
            str(chunk_id_value) if chunk_id_value is not None else f"chunk-{index}"
        )
        start_offset_raw = raw.get("start_offset")
        end_offset_raw = raw.get("end_offset")
        start_offset = start_offset_raw if isinstance(start_offset_raw, int) else 0
        end_offset = end_offset_raw if isinstance(end_offset_raw, int) else len(text)
        chunk_models.append(
            ChunkRecord(
                chunk_id=chunk_id,
                chunk_index=index,
                text=text,
                start_offset=start_offset,
                end_offset=end_offset,
            )
        )
    embeddings = _EMBEDDING_SERVICE.embed(ChunkingOutput(chunks=chunk_models))
    return {
        "embeddings": [embedding.model_dump() for embedding in embeddings.embeddings],
    }


def upsert_qdrant(
    embeddings: list[dict[str, Any]], *, context: dict[str, Any]
) -> dict[str, Any]:
    _ = context
    point_ids = [str(item.get("chunk_id", "")) for item in embeddings]
    return {
        "qdrant_point_ids": [point_id for point_id in point_ids if len(point_id) > 0],
    }


def write_obsidian_summary(
    project: str | None,
    problem: str | None,
    solution: str | None,
    file_path: str,
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    _ = context
    title = project if project is not None else "Memory Summary"
    summary = f"Problem: {problem or 'n/a'}\nSolution: {solution or 'n/a'}"
    return {
        "title": title,
        "summary": summary,
        "obsidian_note_path": f"memory-agent-summaries/{file_path.split('/')[-1]}.md",
    }


def emit_telemetry(
    correlation_id: str,
    status: str,
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    _ = context
    return {
        "correlation_id": correlation_id,
        "status": status,
        "emitted": True,
    }
