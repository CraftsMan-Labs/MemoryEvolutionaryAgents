# Phase 6 TODO - File-Level Progress and Reliability

## Objective
Implement robust stage tracking, retries, reliability controls, and live progress visibility.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Stage Machine
- [x] Implement explicit stage enum and transition policy service.
- [x] Create `file_stage_events` table for timestamped stage events.
- [x] Validate transitions to block illegal stage jumps.
- [x] Record stage durations for performance diagnostics.

### B. Retry and Recovery
- [x] Create `file_retry_queue` table with attempt counters and next-at timestamp.
- [x] Implement retry scheduler with bounded exponential backoff.
- [x] Add poison-file behavior after max retries with clear failure status.
- [x] Ensure retries are idempotent for Qdrant/Obsidian writes.

### C. Live Progress APIs
- [x] Implement `GET /runs/{run_id}/files` with stage and status summaries.
- [x] Implement `GET /files/{file_id}/timeline` with ordered events.
- [x] Implement `POST /files/{file_id}/retry` for manual retry.
- [x] Implement SSE stream endpoint for live progress updates.

### D. Dashboard Experience
- [x] Build file progress page with run-level and file-level views.
- [x] Build file detail panel with stage timeline and latest errors.
- [x] Add filters for source, stage, status, and date.

### E. Reliability Hardening
- [x] Add cron overlap lock and queue safety checks.
- [x] Add cancellation-safe worker shutdown behavior.
- [x] Add timeout handling per processing stage.
- [x] Add dead-letter visibility for persistent failures.

### F. Tests and Load Validation
- [x] Unit tests for stage transition policy.
- [x] Unit tests for retry backoff and max-attempt handling.
- [ ] Integration tests for progress APIs + SSE stream.
- [ ] Load tests for 5k-50k files with retry scenarios.

## Acceptance Criteria
- [x] Each file has complete stage timeline and failure diagnostics.
- [x] Failed files retry automatically with bounded backoff.
- [x] Manual retry works and is audit-tracked.
- [ ] Live progress stream is stable under load.

## Deliverables
- [x] stage event and retry tables
- [x] progress APIs + SSE
- [x] dashboard file progress views
- [ ] reliability and load test suite
