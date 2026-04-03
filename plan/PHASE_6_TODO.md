# Phase 6 TODO - File-Level Progress and Reliability

## Objective
Implement robust stage tracking, retries, reliability controls, and live progress visibility.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Stage Machine
- [ ] Implement explicit stage enum and transition policy service.
- [ ] Create `file_stage_events` table for timestamped stage events.
- [ ] Validate transitions to block illegal stage jumps.
- [ ] Record stage durations for performance diagnostics.

### B. Retry and Recovery
- [ ] Create `file_retry_queue` table with attempt counters and next-at timestamp.
- [ ] Implement retry scheduler with bounded exponential backoff.
- [ ] Add poison-file behavior after max retries with clear failure status.
- [ ] Ensure retries are idempotent for Qdrant/Obsidian writes.

### C. Live Progress APIs
- [ ] Implement `GET /runs/{run_id}/files` with stage and status summaries.
- [ ] Implement `GET /files/{file_id}/timeline` with ordered events.
- [ ] Implement `POST /files/{file_id}/retry` for manual retry.
- [ ] Implement SSE stream endpoint for live progress updates.

### D. Dashboard Experience
- [ ] Build file progress page with run-level and file-level views.
- [ ] Build file detail panel with stage timeline and latest errors.
- [ ] Add filters for source, stage, status, and date.

### E. Reliability Hardening
- [ ] Add cron overlap lock and queue safety checks.
- [ ] Add cancellation-safe worker shutdown behavior.
- [ ] Add timeout handling per processing stage.
- [ ] Add dead-letter visibility for persistent failures.

### F. Tests and Load Validation
- [ ] Unit tests for stage transition policy.
- [ ] Unit tests for retry backoff and max-attempt handling.
- [ ] Integration tests for progress APIs + SSE stream.
- [ ] Load tests for 5k-50k files with retry scenarios.

## Acceptance Criteria
- [ ] Each file has complete stage timeline and failure diagnostics.
- [ ] Failed files retry automatically with bounded backoff.
- [ ] Manual retry works and is audit-tracked.
- [ ] Live progress stream is stable under load.

## Deliverables
- [ ] stage event and retry tables
- [ ] progress APIs + SSE
- [ ] dashboard file progress views
- [ ] reliability and load test suite
