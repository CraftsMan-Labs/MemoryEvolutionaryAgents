from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Json

from .contracts import (
    CanonicalMemoryPersistRequest,
    CanonicalMemoryPersistResponse,
    MemoryChunkPersistRequest,
    WorkflowStageEventRequest,
)


class PostgresConnectionFactory:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        with Connection.connect(self._database_url, row_factory=dict_row) as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise


class Phase2Repository:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def persist_memory(
        self, request: CanonicalMemoryPersistRequest
    ) -> CanonicalMemoryPersistResponse:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO canonical_memories(
                      source_id,
                      source_path,
                      file_path,
                      content_hash,
                      project,
                      problem,
                      solution,
                      event_date,
                      extraction_confidence,
                      tags,
                      entities,
                      obsidian_note_path,
                      qdrant_point_ids,
                      ontology_terms,
                      taxonomy_tags,
                      relation_edges
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, file_path, content_hash) DO UPDATE
                    SET project = EXCLUDED.project,
                        problem = EXCLUDED.problem,
                        solution = EXCLUDED.solution,
                        event_date = EXCLUDED.event_date,
                        extraction_confidence = EXCLUDED.extraction_confidence,
                        tags = EXCLUDED.tags,
                        entities = EXCLUDED.entities,
                        obsidian_note_path = EXCLUDED.obsidian_note_path,
                        qdrant_point_ids = EXCLUDED.qdrant_point_ids,
                        ontology_terms = EXCLUDED.ontology_terms,
                        taxonomy_tags = EXCLUDED.taxonomy_tags,
                        relation_edges = EXCLUDED.relation_edges,
                        updated_at = NOW()
                    RETURNING id
                    """,
                    (
                        request.source_id,
                        request.source_path,
                        request.file_path,
                        request.content_hash,
                        request.project,
                        request.problem,
                        request.solution,
                        request.event_date,
                        request.extraction_confidence,
                        Json(request.tags),
                        Json(request.entities),
                        request.obsidian_note_path,
                        Json(request.qdrant_point_ids),
                        Json(request.ontology_terms),
                        Json(request.taxonomy_tags),
                        Json(request.relation_edges),
                    ),
                )
                row = cur.fetchone()
        if row is None:
            raise RuntimeError("failed to persist canonical memory")
        return CanonicalMemoryPersistResponse(memory_id=int(row["id"]))

    def persist_chunk(self, request: MemoryChunkPersistRequest) -> None:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO memory_chunks(
                      memory_id,
                      chunk_id,
                      chunk_index,
                      chunk_text,
                      start_offset,
                      end_offset,
                      vector_size
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (memory_id, chunk_id) DO UPDATE
                    SET chunk_index = EXCLUDED.chunk_index,
                        chunk_text = EXCLUDED.chunk_text,
                        start_offset = EXCLUDED.start_offset,
                        end_offset = EXCLUDED.end_offset,
                        vector_size = EXCLUDED.vector_size,
                        updated_at = NOW()
                    """,
                    (
                        request.memory_id,
                        request.chunk_id,
                        request.chunk_index,
                        request.chunk_text,
                        request.start_offset,
                        request.end_offset,
                        request.vector_size,
                    ),
                )

    def record_stage_event(self, request: WorkflowStageEventRequest) -> None:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflow_stage_events(
                      run_id,
                      file_run_id,
                      source_id,
                      file_path,
                      stage,
                      status,
                      error_code,
                      error_message,
                      recorded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request.run_id,
                        request.file_run_id,
                        request.source_id,
                        request.file_path,
                        request.stage,
                        request.status.value,
                        request.error_code,
                        request.error_message,
                        request.recorded_at,
                    ),
                )
