# Phase 0 TODO - Project Bootstrap

## Objective
Stand up the baseline platform stack (API, worker, dashboard, Postgres, Qdrant), establish shared project structure, and enforce coding guardrails from day one.

## Implementation Status
- Completed for v1 baseline in current repository.
- Scope delivered with Docker stack bootstrap, service wiring, migration runner, startup/health validation, and local developer runbooks.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Repository and Service Skeletons
- [x] Create service directories for `api`, `worker`, `dashboard`, and shared libraries.
- [x] Define object-oriented module boundaries (`services`, `repositories`, `adapters`, `models`, `api`).
- [x] Add typed configuration models with explicit input/output for each service.
- [x] Add startup entrypoints with clear dependency wiring and no business logic in boot files.

### B. Docker and Runtime Foundations
- [x] Create `docker-compose.yml` for API, worker, dashboard, Postgres, and Qdrant.
- [x] Add health checks for each service and dependency.
- [x] Add `.env.example` with explicit required and optional fields.
- [x] Add local developer start command(s) in docs.

### C. Database Baseline
- [x] Set up migration framework and first migration baseline.
- [x] Add foundational tables required before feature phases (users, settings, system metadata).
- [x] Create repository interfaces for DB operations with explicit return types.
- [x] Add DB connection lifecycle management with predictable error handling.

### D. API and Worker Baseline
- [x] Implement base FastAPI app factory and router registration pattern.
- [x] Add worker service boot with scheduler loop placeholder and graceful shutdown.
- [x] Add shared error response envelope models.
- [x] Add request correlation IDs for logs/traces.

### E. Quality and Tooling
- [x] Add formatting/lint/type-check configs for touched languages.
- [x] Add baseline tests for service startup and health endpoints.
- [x] Add CI/local command checklist for build, lint, and tests.

## Acceptance Criteria
- [x] All containers start successfully with health checks passing.
- [x] API and worker start with typed config validation.
- [x] Baseline migration applies cleanly on a fresh DB.
- [x] No module contains mixed responsibilities.

## Deliverables
- [x] `docker-compose.yml`
- [x] `.env.example`
- [x] migration bootstrap
- [x] service skeleton structure with typed interfaces
