# Phase 5 TODO - Telemetry, Cost, and Status

## Objective
Add traceability, token/cost accounting, and operational status visibility across ingestion and chat.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Telemetry Model and Storage
- [ ] Create `model_pricing` table with versioned pricing records.
- [ ] Create `token_usage_events` table with explicit usage dimensions.
- [ ] Define typed telemetry event models for runs/nodes/stages.

### B. Langfuse Integration
- [ ] Implement `TelemetryAdapter` interface for Langfuse emission.
- [ ] Add run-level and node-level span emission from worker.
- [ ] Add chat request telemetry with retrieval and synthesis span context.
- [ ] Add failure emission path with typed error classification.

### C. Cost Computation
- [ ] Implement cost calculator service using pricing version at event time.
- [ ] Persist computed costs by run and by request.
- [ ] Add guardrails for missing pricing records with actionable errors.

### D. Status and Metrics APIs
- [ ] Implement status endpoints for job health, connector health, and freshness.
- [ ] Implement metrics endpoints for token and cost trends.
- [ ] Add dashboard widgets for run health and usage costs.

### E. Tests
- [ ] Unit tests for cost computation across pricing versions.
- [ ] Unit tests for telemetry event mapping and error paths.
- [ ] Integration tests for end-to-end telemetry from ingest/chat.
- [ ] API tests for status and metrics payload contracts.

## Acceptance Criteria
- [ ] Every ingest/chat run emits traceable telemetry spans.
- [ ] Token and cost metrics are accurate and queryable.
- [ ] Status page reflects connector and job health in near-real time.
- [ ] Cost computation logic is centralized and non-duplicated.

## Deliverables
- [ ] telemetry adapter and integration
- [ ] pricing and token usage persistence
- [ ] status and metrics APIs with dashboard widgets
