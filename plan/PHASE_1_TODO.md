# Phase 1 TODO - Ingestion Foundation

## Objective
Implement source registry, incremental scanning, and cron-based ingestion orchestration with reliable per-file tracking.

## Implementation Status
- Completed for v1 baseline in current repository.
- Scope delivered with source registry, incremental scanner, overlap-safe scheduler, run/file tracking, and expanded tests.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Source Registry
- [x] Implement source tables with lifecycle state (`active`, `paused`, `deleted`).
- [x] Add repository and service classes for source CRUD with explicit DTOs.
- [x] Add APIs for source create/update/list operations.
- [x] Support hot updates so newly added sources are picked up next cron cycle.

### B. Incremental Scanner
- [x] Implement scanner service with stable fingerprint (`path + mtime + hash`).
- [x] Add deduplication logic and cursor persistence.
- [x] Separate file discovery from ingestion execution responsibilities.
- [x] Add source-level scan stats (last scan, errors, file counts).

### C. Cron Scheduler
- [x] Implement scheduler loop with configurable cadence (5-10 minutes).
- [x] Add overlap lock to prevent concurrent ingestion runs.
- [x] Add run metadata records (`started_at`, `ended_at`, `status`).
- [x] Add graceful cancellation and timeout handling.

### D. File Run Tracking
- [x] Create `ingestion_runs`, `ingested_files`, and `file_processing_runs` tables.
- [x] Implement typed repository methods to create/update file run state.
- [x] Record per-file errors with actionable typed error code and message.
- [x] Add APIs for run-level and file-level progress listing.

### E. Tests
- [x] Unit tests for fingerprinting and dedup behavior.
- [x] Unit tests for source lifecycle transitions.
- [x] Integration tests for cron trigger and overlap lock.
- [x] Integration tests for scanner + run persistence.

## Acceptance Criteria
- [x] New and updated files are detected once per change and ingested once per run.
- [x] Source lifecycle controls take effect without service restart.
- [x] Cron runs are idempotent and overlap-safe.
- [x] Per-file tracking is queryable through API.

## Deliverables
- [x] source management APIs
- [x] incremental scanner and cron runner
- [x] run/file tracking tables and APIs
