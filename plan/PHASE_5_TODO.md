# Phase 5 TODO - Telemetry, Cost, and Status

## Objective
Add traceability, token/cost accounting, and operational status visibility across ingestion and chat.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Telemetry Model and Storage
- [x] Create `model_pricing` table with versioned pricing records.
- [x] Create `token_usage_events` table with explicit usage dimensions.
- [x] Define typed telemetry event models for runs/nodes/stages.

### B. Langfuse Integration
- [x] Implement `TelemetryAdapter` interface for Langfuse emission.
- [x] Add run-level and node-level span emission from worker.
- [x] Add chat request telemetry with retrieval and synthesis span context.
- [x] Add failure emission path with typed error classification.

### C. Cost Computation
- [x] Implement cost calculator service using pricing version at event time.
- [x] Persist computed costs by run and by request.
- [x] Add guardrails for missing pricing records with actionable errors.

### D. Status and Metrics APIs
- [x] Implement status endpoints for job health, connector health, and freshness.
- [x] Implement metrics endpoints for token and cost trends.
- [x] Add dashboard widgets for run health and usage costs.

### E. Tests
- [x] Unit tests for cost computation across pricing versions.
- [x] Unit tests for telemetry event mapping and error paths.
- [x] Integration tests for end-to-end telemetry from ingest/chat.
- [x] API tests for status and metrics payload contracts.

## Acceptance Criteria
- [x] Every ingest/chat run emits traceable telemetry spans.
- [x] Token and cost metrics are accurate and queryable.
- [x] Status page reflects connector and job health in near-real time.
- [x] Cost computation logic is centralized and non-duplicated.

## Deliverables
- [x] telemetry adapter and integration
- [x] pricing and token usage persistence
- [x] status and metrics APIs with dashboard widgets
