from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory_evolutionary_agents.phase2.contracts import ChunkRecord, ChunkingOutput
from memory_evolutionary_agents.phase2.handlers import (
    ChunkingService,
    EmbeddingService,
    NormalizationService,
)

_NORMALIZATION_SERVICE = NormalizationService()
_CHUNKING_SERVICE = ChunkingService()
_EMBEDDING_SERVICE = EmbeddingService.from_env()


def _context_get(context: dict[str, Any], *path: str) -> object | None:
    current: object = context
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _normalized_string(value: object, *, allow_topic: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if len(stripped) == 0:
        return ""
    if "{{" in stripped and "}}" in stripped:
        return None
    if allow_topic is False and stripped.startswith("phase2."):
        return None
    return value


def _resolve_string(
    values: list[object],
    *,
    allow_topic: bool = False,
) -> str | None:
    for value in values:
        normalized = _normalized_string(value, allow_topic=allow_topic)
        if normalized is None:
            continue
        return normalized
    return None


def _resolve_list(values: list[object]) -> list[dict[str, Any]]:
    for value in values:
        if isinstance(value, list):
            dict_items = [item for item in value if isinstance(item, dict)]
            if len(dict_items) > 0:
                return dict_items
    return []


def normalize_file(
    file_path: str | None = None,
    *,
    file_content: str | None = None,
    email_text: str | None = None,
    payload: dict[str, Any] | None = None,
    context: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    _ = context
    _ = extra
    resolved_file_path = _resolve_string(
        [
            file_path,
            None if payload is None else payload.get("file_path"),
            _context_get(context, "input", "file_path"),
        ]
    )
    if resolved_file_path is None:
        resolved_file_path = "unknown"
    resolved_content = _resolve_string(
        [
            file_content,
            email_text,
            None if payload is None else payload.get("file_content"),
            _context_get(context, "input", "file_content"),
        ]
    )
    if resolved_content is None:
        resolved_content = ""
    normalized = _NORMALIZATION_SERVICE.normalize(
        file_path=resolved_file_path, file_content=resolved_content
    )
    return {
        "document_text": normalized.document_text,
        "document_type": normalized.document_type,
        "metadata": normalized.metadata,
    }


def chunk_document(
    document_text: str | None = None,
    *,
    email_text: str | None = None,
    payload: dict[str, Any] | None = None,
    context: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    _ = extra
    resolved_text = _resolve_string(
        [
            document_text,
            email_text,
            None if payload is None else payload.get("document_text"),
            _context_get(
                context, "outputs", "normalize_file", "output", "document_text"
            ),
            _context_get(context, "nodes", "normalize_file", "output", "document_text"),
            _context_get(context, "input", "file_content"),
        ]
    )
    if resolved_text is None:
        resolved_text = ""
    chunks = _CHUNKING_SERVICE.chunk(resolved_text)
    return {
        "chunks": [chunk.model_dump() for chunk in chunks.chunks],
    }


def embed_chunks(
    chunks: list[dict[str, Any]] | None = None,
    *,
    payload: dict[str, Any] | None = None,
    context: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    _ = context
    _ = extra
    resolved_chunks = _resolve_list(
        [
            chunks,
            None if payload is None else payload.get("chunks"),
            _context_get(context, "outputs", "chunk_document", "output", "chunks"),
            _context_get(context, "nodes", "chunk_document", "output", "chunks"),
        ]
    )
    chunk_models: list[ChunkRecord] = []
    for index, raw in enumerate(resolved_chunks):
        raw_item: dict[str, Any] | None = None
        if isinstance(raw, dict):
            raw_item = raw
        elif isinstance(raw, str):
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, dict):
                    raw_item = decoded
            except ValueError:
                raw_item = None
        if raw_item is None:
            continue
        text_value = raw_item.get("text")
        text = text_value if isinstance(text_value, str) else ""
        chunk_id_value = raw_item.get("chunk_id")
        chunk_id = (
            str(chunk_id_value) if chunk_id_value is not None else f"chunk-{index}"
        )
        start_offset_raw = raw_item.get("start_offset")
        end_offset_raw = raw_item.get("end_offset")
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
    embeddings: list[dict[str, Any]] | None = None,
    *,
    payload: dict[str, Any] | None = None,
    context: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    _ = context
    _ = extra
    resolved_embeddings = _resolve_list(
        [
            embeddings,
            None if payload is None else payload.get("embeddings"),
            _context_get(context, "outputs", "embed_chunks", "output", "embeddings"),
            _context_get(context, "nodes", "embed_chunks", "output", "embeddings"),
        ]
    )
    point_ids: list[str] = []
    for item in resolved_embeddings:
        if isinstance(item, dict):
            point_ids.append(str(item.get("chunk_id", "")))
            continue
        if isinstance(item, str):
            try:
                decoded = json.loads(item)
            except ValueError:
                continue
            if isinstance(decoded, dict):
                point_ids.append(str(decoded.get("chunk_id", "")))
    return {
        "qdrant_point_ids": [point_id for point_id in point_ids if len(point_id) > 0],
    }


def write_obsidian_summary(
    project: str | None = None,
    problem: str | None = None,
    solution: str | None = None,
    file_path: str | None = None,
    *,
    payload: dict[str, Any] | None = None,
    context: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    _ = context
    _ = extra
    resolved_project = _resolve_string(
        [
            project,
            None if payload is None else payload.get("project"),
            _context_get(
                context,
                "outputs",
                "extract_structured_memory",
                "output",
                "project",
            ),
            _context_get(
                context, "nodes", "extract_structured_memory", "output", "project"
            ),
        ]
    )
    resolved_problem = _resolve_string(
        [
            problem,
            None if payload is None else payload.get("problem"),
            _context_get(
                context,
                "outputs",
                "extract_structured_memory",
                "output",
                "problem",
            ),
            _context_get(
                context, "nodes", "extract_structured_memory", "output", "problem"
            ),
        ]
    )
    resolved_solution = _resolve_string(
        [
            solution,
            None if payload is None else payload.get("solution"),
            _context_get(
                context,
                "outputs",
                "extract_structured_memory",
                "output",
                "solution",
            ),
            _context_get(
                context, "nodes", "extract_structured_memory", "output", "solution"
            ),
        ]
    )
    resolved_file_path = _resolve_string(
        [
            file_path,
            None if payload is None else payload.get("file_path"),
            _context_get(context, "input", "file_path"),
        ]
    )
    if resolved_file_path is None:
        resolved_file_path = "unknown"
    title = resolved_project if resolved_project is not None else "Memory Summary"
    summary = (
        f"Problem: {resolved_problem or 'n/a'}\nSolution: {resolved_solution or 'n/a'}"
    )
    return {
        "title": title,
        "summary": summary,
        "obsidian_note_path": f"memory-agent-summaries/{Path(resolved_file_path).stem}.md",
    }


def emit_telemetry(
    correlation_id: str | None = None,
    status: str | None = None,
    *,
    payload: dict[str, Any] | None = None,
    context: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    _ = context
    _ = extra
    resolved_correlation_id = _resolve_string(
        [
            correlation_id,
            None if payload is None else payload.get("correlation_id"),
            _context_get(context, "input", "correlation_id"),
        ]
    )
    resolved_status = _resolve_string(
        [status, None if payload is None else payload.get("status")],
        allow_topic=True,
    )
    if resolved_correlation_id is None:
        resolved_correlation_id = "unknown"
    if resolved_status is None:
        resolved_status = "unknown"
    return {
        "correlation_id": resolved_correlation_id,
        "status": resolved_status,
        "emitted": True,
    }
