# Phase 4 TODO - Retrieval and Chat Orchestration

## Objective
Implement dual retrieval (vector + metadata and Obsidian link-walk) and a synthesis layer that returns cited answers.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Query Contracts
- [x] Define explicit chat request/response models with filters and citation fields.
- [x] Add query validation for date/project/tag/ontology filter combinations.
- [x] Define retrieval result DTO used by both pipelines.

### B. Pipeline A - Vector + Metadata
- [x] Implement vector retrieval service over Qdrant with metadata filters.
- [x] Add score normalization and top-k configuration.
- [x] Add deterministic post-filtering for strict filters.

### C. Pipeline B - Obsidian Link Walk
- [x] Implement link graph reader service from Obsidian notes.
- [x] Implement bounded neighborhood traversal with depth and fanout limits.
- [x] Add deduplication and ranking for linked context candidates.

### D. Final Synthesis
- [x] Implement synthesis workflow node combining both retrieval contexts.
- [x] Enforce citation output format (source path, note path, chunk id when available).
- [x] Add confidence scoring in final response model.

### E. API and UI Integration
- [x] Implement `POST /chat/query` orchestration in API service.
- [x] Add chat UI with filter controls and citation rendering.
- [x] Add retrieval diagnostics field for debugging (optional in UI, available in API logs).

### F. Tests
- [x] Unit tests for filter parsing and validation.
- [x] Unit tests for link-walk traversal bounds and dedup.
- [x] Integration tests for dual retrieval + synthesis path.
- [x] Golden tests for citation format stability.

## Acceptance Criteria
- [x] Chat combines both retrieval strategies every request.
- [x] Responses include citations and confidence.
- [x] Filters correctly constrain retrieval results.
- [x] Retrieval code remains modular with no duplicated ranking logic.

## Deliverables
- [x] `workflows/chat_vector_retrieval_v1.yaml`
- [x] `workflows/chat_linkwalk_retrieval_v1.yaml`
- [x] `workflows/chat_synthesis_v1.yaml`
- [x] chat API and UI integration
