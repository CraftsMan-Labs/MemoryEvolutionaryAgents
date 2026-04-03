# Phase 3 TODO - Dynamic Ontology and Taxonomy Evolution

## Objective
Add dynamic ontology/taxonomy/relation evolution with provisional terms and a review queue.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Schema and Models
- [x] Create tables: `ontology_terms`, `taxonomy_tags`, `relations`, `schema_proposals`.
- [x] Define explicit typed models for term, tag, relation, and proposal contracts.
- [x] Define status model for proposals (`provisional`, `approved`, `rejected`, `merged`).

### B. Classification and Matching
- [x] Implement ontology matcher service against existing registry.
- [x] Add confidence scoring with deterministic threshold config.
- [x] Add fallback proposal creation when confidence is below threshold.
- [x] Ensure provisional terms are immediately usable for retrieval/filtering.

### C. Proposal and Review Flow
- [x] Implement proposal queue APIs (list/detail/approve/reject/merge).
- [x] Implement merge operation to deduplicate semantically similar terms.
- [x] Add audit trail for who changed proposal state and when.
- [x] Add worker-safe idempotent operations for repeated runs.

### D. Workflow Integration
- [x] Create `workflows/ontology_evolution_v1.yaml` with explicit schemas.
- [x] Integrate ontology evolution workflow into ingestion pipeline.
- [x] Persist mapped ontology/taxonomy fields into canonical memory and Qdrant payload.

### E. Tests
- [x] Unit tests for matcher confidence and threshold behavior.
- [x] Unit tests for proposal lifecycle transitions.
- [x] Integration tests for ingest-triggered proposal creation.
- [x] Integration tests for approval/merge effects on retrieval filters.

## Acceptance Criteria
- [x] Existing terms are reused when confidence is sufficient.
- [x] New unknown concepts create provisional proposals automatically.
- [x] Review queue provides complete and actionable proposal context.
- [x] No duplicated matching logic across services/workflows.

## Deliverables
- [x] ontology/taxonomy/relation schema and APIs
- [x] `workflows/ontology_evolution_v1.yaml`
- [x] proposal review queue with tests
