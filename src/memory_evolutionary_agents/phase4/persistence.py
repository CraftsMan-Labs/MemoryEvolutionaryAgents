from __future__ import annotations

from datetime import date
from typing import Any, cast

from ..phase2.persistence import PostgresConnectionFactory
from .contracts import CanonicalMemoryRecord, ChatQueryFilters, MemoryChunkRecord


class Phase4Repository:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def list_memories_for_filters(
        self,
        filters: ChatQueryFilters,
        limit: int,
    ) -> list[CanonicalMemoryRecord]:
        clauses: list[str] = []
        params: list[object] = []
        if filters.project is not None:
            clauses.append("project = %s")
            params.append(filters.project)
        query = """
            SELECT
              id,
              source_path,
              file_path,
              project,
              event_date,
              tags,
              ontology_terms,
              taxonomy_tags,
              obsidian_note_path
            FROM canonical_memories
        """
        if len(clauses) > 0:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC LIMIT %s"
        params.append(limit)

        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(cast(Any, query), tuple(params))
                rows = cast(list[dict[str, Any]], cur.fetchall())
        records = [_memory_from_row(row) for row in rows]
        return [record for record in records if _matches_filters(record, filters)]

    def list_memories_by_note_paths(
        self,
        note_paths: list[str],
    ) -> list[CanonicalMemoryRecord]:
        if len(note_paths) == 0:
            return []
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      id,
                      source_path,
                      file_path,
                      project,
                      event_date,
                      tags,
                      ontology_terms,
                      taxonomy_tags,
                      obsidian_note_path
                    FROM canonical_memories
                    WHERE obsidian_note_path = ANY(%s)
                    """,
                    (note_paths,),
                )
                rows = cast(list[dict[str, Any]], cur.fetchall())
        return [_memory_from_row(row) for row in rows]

    def list_chunks_for_memory_ids(
        self,
        memory_ids: list[int],
    ) -> list[MemoryChunkRecord]:
        if len(memory_ids) == 0:
            return []
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT memory_id, chunk_id, chunk_index, chunk_text
                    FROM memory_chunks
                    WHERE memory_id = ANY(%s)
                    ORDER BY memory_id ASC, chunk_index ASC
                    """,
                    (memory_ids,),
                )
                rows = cast(list[dict[str, Any]], cur.fetchall())
        chunks: list[MemoryChunkRecord] = []
        for row in rows:
            chunks.append(
                MemoryChunkRecord(
                    memory_id=int(row["memory_id"]),
                    chunk_id=str(row["chunk_id"]),
                    chunk_index=int(row["chunk_index"]),
                    chunk_text=str(row["chunk_text"]),
                )
            )
        return chunks


def _memory_from_row(row: dict[str, Any]) -> CanonicalMemoryRecord:
    return CanonicalMemoryRecord(
        id=int(row["id"]),
        source_path=str(row["source_path"]),
        file_path=str(row["file_path"]),
        project=cast(str | None, row.get("project")),
        event_date=cast(str | None, row.get("event_date")),
        tags=_string_list(row.get("tags")),
        ontology_terms=_string_list(row.get("ontology_terms")),
        taxonomy_tags=_string_list(row.get("taxonomy_tags")),
        obsidian_note_path=cast(str | None, row.get("obsidian_note_path")),
    )


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                result.append(item)
        return result
    return []


def _matches_filters(memory: CanonicalMemoryRecord, filters: ChatQueryFilters) -> bool:
    if filters.project is not None and memory.project != filters.project:
        return False
    if _contains_all(memory.tags, filters.tags) is False:
        return False
    if _contains_all(memory.ontology_terms, filters.ontology_terms) is False:
        return False
    if _contains_all(memory.taxonomy_tags, filters.taxonomy_tags) is False:
        return False

    if filters.event_date_from is None and filters.event_date_to is None:
        return True
    if memory.event_date is None:
        return False
    try:
        memory_date = date.fromisoformat(memory.event_date)
    except ValueError:
        return False
    if filters.event_date_from is not None:
        if memory_date < date.fromisoformat(filters.event_date_from):
            return False
    if filters.event_date_to is not None:
        if memory_date > date.fromisoformat(filters.event_date_to):
            return False
    return True


def _contains_all(haystack: list[str], needles: list[str]) -> bool:
    if len(needles) == 0:
        return True
    lowered_haystack = {value.lower() for value in haystack}
    for needle in needles:
        if needle.lower() not in lowered_haystack:
            return False
    return True
