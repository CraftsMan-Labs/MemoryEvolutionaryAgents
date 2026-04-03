from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RegistryStatus(str, Enum):
    PROVISIONAL = "provisional"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


class ProposalStatus(str, Enum):
    PROVISIONAL = "provisional"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


class ProposalType(str, Enum):
    ONTOLOGY_TERM = "ontology_term"
    TAXONOMY_TAG = "taxonomy_tag"
    RELATION = "relation"


class RegistryTermRecord(BaseModel):
    id: int
    name: str
    normalized_name: str
    status: RegistryStatus
    merged_into_id: int | None


class RelationRecord(BaseModel):
    id: int
    source_term_id: int
    predicate: str
    target_term_id: int
    status: RegistryStatus


class SchemaProposalRecord(BaseModel):
    id: int
    proposal_type: ProposalType
    candidate_value: str
    normalized_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: ProposalStatus
    context: dict[str, object]
    linked_record_id: int | None
    merged_into_record_id: int | None
    created_at: datetime
    updated_at: datetime


class SchemaProposalStateEventRecord(BaseModel):
    id: int
    proposal_id: int
    from_status: ProposalStatus | None
    to_status: ProposalStatus
    changed_by: str
    note: str | None
    changed_at: datetime


class OntologyEvolutionRequest(BaseModel):
    source_id: int
    source_path: str
    file_path: str
    content_hash: str
    project: str | None
    tags: list[str]
    entities: list[str]
    actor: str = "worker"


class RelationEdge(BaseModel):
    source: str
    predicate: str
    target: str
    status: RegistryStatus


class OntologyEvolutionResult(BaseModel):
    ontology_terms: list[str]
    taxonomy_tags: list[str]
    relation_edges: list[RelationEdge]
    proposal_ids: list[int]


class ProposalListResponse(BaseModel):
    proposals: list[SchemaProposalRecord]


class ProposalDetailResponse(BaseModel):
    proposal: SchemaProposalRecord
    events: list[SchemaProposalStateEventRecord]


class ProposalDecisionRequest(BaseModel):
    actor: str = Field(min_length=1)
    note: str | None = None


class ProposalMergeRequest(BaseModel):
    actor: str = Field(min_length=1)
    target_record_id: int = Field(gt=0)
    note: str | None = None


class FilterAliasResolutionRequest(BaseModel):
    ontology_terms: list[str]
    taxonomy_tags: list[str]


class FilterAliasResolutionResponse(BaseModel):
    ontology_terms: list[str]
    taxonomy_tags: list[str]
    ontology_aliases: dict[str, str]
    taxonomy_aliases: dict[str, str]
