from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class StageStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class IngestWorkflowInput(BaseModel):
    run_id: int
    file_run_id: int
    source_id: int
    source_path: str
    file_path: str
    file_content: str
    correlation_id: str


class NormalizeOutput(BaseModel):
    document_text: str
    document_type: str
    metadata: dict[str, str]


class ExtractionOutput(BaseModel):
    project: str | None = None
    problem: str | None = None
    solution: str | None = None
    event_date: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class ClassificationOutput(BaseModel):
    tags: list[str]
    entities: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class ChunkRecord(BaseModel):
    chunk_id: str
    chunk_index: int
    text: str
    start_offset: int
    end_offset: int


class ChunkingOutput(BaseModel):
    chunks: list[ChunkRecord]


class EmbeddingRecord(BaseModel):
    chunk_id: str
    vector: list[float]
    model_name: str


class EmbeddingOutput(BaseModel):
    embeddings: list[EmbeddingRecord]


class QdrantPoint(BaseModel):
    point_id: str
    vector: list[float]
    payload: dict[str, object]


class QdrantUpsertRequest(BaseModel):
    points: list[QdrantPoint]


class QdrantUpsertResponse(BaseModel):
    stored_point_ids: list[str]


class ObsidianWriteRequest(BaseModel):
    source_path: str
    file_path: str
    title: str
    body: str


class ObsidianWriteResponse(BaseModel):
    note_path: str


class CanonicalMemoryPersistRequest(BaseModel):
    source_id: int
    source_path: str
    file_path: str
    content_hash: str
    project: str | None
    problem: str | None
    solution: str | None
    event_date: str | None
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    tags: list[str]
    entities: list[str]
    obsidian_note_path: str | None
    qdrant_point_ids: list[str]
    ontology_terms: list[str]
    taxonomy_tags: list[str]
    relation_edges: list[dict[str, str]]


class CanonicalMemoryPersistResponse(BaseModel):
    memory_id: int


class MemoryChunkPersistRequest(BaseModel):
    memory_id: int
    chunk_id: str
    chunk_index: int
    chunk_text: str
    start_offset: int
    end_offset: int
    vector_size: int


class WorkflowStageEventRequest(BaseModel):
    run_id: int
    file_run_id: int
    source_id: int
    file_path: str
    stage: str
    status: StageStatus
    error_code: str | None
    error_message: str | None
    recorded_at: datetime


class WorkflowExecutionResult(BaseModel):
    status: WorkflowStatus
    raw_output: dict[str, object]


class StructuredMemoryResult(BaseModel):
    project: str | None
    problem: str | None
    solution: str | None
    date: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    tags: list[str]
    entities: list[str]
    obsidian_note_path: str | None
    qdrant_point_ids: list[str]
    chunks: list[ChunkRecord]
    embeddings: list[EmbeddingRecord]
