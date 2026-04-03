from __future__ import annotations

from pydantic import BaseModel, Field


class ChatQueryFilters(BaseModel):
    project: str | None = None
    tags: list[str] = Field(default_factory=list)
    ontology_terms: list[str] = Field(default_factory=list)
    taxonomy_tags: list[str] = Field(default_factory=list)
    event_date_from: str | None = None
    event_date_to: str | None = None


class ChatQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=20)
    vector_top_k: int = Field(default=8, ge=1, le=40)
    link_depth: int = Field(default=2, ge=0, le=4)
    link_fanout: int = Field(default=6, ge=1, le=20)
    filters: ChatQueryFilters = Field(default_factory=ChatQueryFilters)


class CitationRecord(BaseModel):
    source_path: str
    note_path: str | None
    chunk_id: str | None


class RetrievalResultRecord(BaseModel):
    memory_id: int
    source_path: str
    file_path: str
    note_path: str | None
    chunk_id: str | None
    snippet: str
    score: float = Field(ge=0.0)
    normalized_score: float = Field(ge=0.0, le=1.0)
    retrieval_path: str


class RetrievalDiagnostics(BaseModel):
    vector_candidates: int
    vector_kept: int
    linkwalk_candidates: int
    linkwalk_kept: int
    resolved_ontology_aliases: dict[str, str]
    resolved_taxonomy_aliases: dict[str, str]


class ChatQueryResponse(BaseModel):
    request_id: str | None = None
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[CitationRecord]
    retrieval_diagnostics: RetrievalDiagnostics


class CanonicalMemoryRecord(BaseModel):
    id: int
    source_path: str
    file_path: str
    project: str | None
    event_date: str | None
    tags: list[str]
    ontology_terms: list[str]
    taxonomy_tags: list[str]
    obsidian_note_path: str | None


class MemoryChunkRecord(BaseModel):
    memory_id: int
    chunk_id: str
    chunk_index: int
    chunk_text: str


class QdrantSearchRequest(BaseModel):
    vector: list[float]
    limit: int = Field(ge=1, le=100)
    project: str | None = None
    tags: list[str] = Field(default_factory=list)
    ontology_terms: list[str] = Field(default_factory=list)
    taxonomy_tags: list[str] = Field(default_factory=list)


class QdrantScoredPoint(BaseModel):
    point_id: str
    score: float
    payload: dict[str, object]


class QdrantSearchResponse(BaseModel):
    points: list[QdrantScoredPoint]


class LinkWalkRequest(BaseModel):
    seed_note_paths: list[str]
    max_depth: int = Field(ge=0, le=4)
    max_fanout: int = Field(ge=1, le=20)


class LinkWalkCandidate(BaseModel):
    note_path: str
    depth: int = Field(ge=0)


class LinkWalkResponse(BaseModel):
    candidates: list[LinkWalkCandidate]
