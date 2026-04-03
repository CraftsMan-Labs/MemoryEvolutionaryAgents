# Phase 2 TODO - SimpleAgents YAML Pipelines (Core)

## Objective
Build the core ingestion workflow that normalizes source files, extracts structured memory, writes Obsidian summaries, and upserts vector data into Qdrant.

## Implementation Status
- Completed for v1 baseline in current repository.
- Scope delivered with strict workflow output validation, Postgres canonical persistence, typed adapters/services, deterministic handlers, fixture-based regression tests, and env-gated end-to-end integration coverage.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Workflow Contracts
- [x] Define explicit input/output schema for `ingest_memory_v1` workflow.
- [x] Define per-node output schemas for all `llm_call` nodes.
- [x] Define deterministic worker contracts for non-LLM tasks.
- [x] Add shared schema models to avoid duplicated payload definitions.

### B. Pipeline Nodes
- [x] Implement normalize node (encoding cleanup, document typing, metadata extraction).
- [x] Implement extraction node for `project/problem/solution/date`.
- [x] Implement classification node for tags/entities.
- [x] Implement chunking node with deterministic chunk boundaries.
- [x] Implement embedding node and Qdrant upsert node.
- [x] Implement Obsidian summary write node.
- [x] Implement telemetry emit node.

### C. Adapters and Services
- [x] Implement `QdrantAdapter` interface with typed upsert/query methods.
- [x] Implement `ObsidianAdapter` interface with typed write/update methods.
- [x] Implement extraction service class with strict output validation.
- [x] Implement workflow runner integration from worker.

### D. Data Persistence
- [x] Persist canonical memory records and extraction confidence.
- [x] Persist Qdrant payload metadata including Obsidian link fields.
- [x] Persist workflow stage events for each file run.

### E. Regression Fixtures and Tests
- [x] Add fixture set for representative files across sources.
- [x] Add extraction quality regression tests (success/failure).
- [x] Add integration test for end-to-end ingest -> Postgres/Qdrant/Obsidian.
- [x] Add schema validation tests for each workflow node output.

## Acceptance Criteria
- [x] Workflow runs end-to-end for a sample batch with no ambiguous payloads.
- [x] Structured outputs always include required fields or typed failure reason.
- [x] Qdrant and Obsidian are updated consistently for processed files.
- [x] No duplicated transformation logic across nodes/services.

## Deliverables
- [x] `workflows/ingest_memory_v1.yaml`
- [x] deterministic worker handlers
- [x] extraction fixtures and regression tests
