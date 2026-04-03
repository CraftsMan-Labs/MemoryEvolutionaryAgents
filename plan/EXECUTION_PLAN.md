# Memory Evolutionary Agents - Execution Plan

## Goal
Build an evolutionary memory system that ingests session data from local agent folders, extracts structured memory, synchronizes with Obsidian for human readability, indexes in Qdrant for semantic retrieval, and exposes a dashboard with chat, telemetry, and file-level progress.

## Engineering Guardrails (Mandatory)
- Object-oriented design with clear responsibilities per class/service.
- Keep code KISS and DRY: small focused units, no duplicated logic, straightforward control flow.
- Keep code concise and readable for humans; avoid clever abstractions and code smells.
- Every function/method must have explicit input and explicit output contracts (typed request/response models, DTOs, or dataclasses).
- Avoid ambiguous truthy/falsy checks for nullable typed fields; use explicit null/none checks.
- Prefer reusable shared utilities over one-off helpers in feature modules.
- Add tests for both success and failure paths for each new behavior.
- Use `uv` for Python environment/dependency workflows and `bun` for Vue workflows.

## Scope (v1)
- Sources: `~/.claude`, `~/.codex`, `~/.opencode`, plus user-added folder paths from the portal.
- Local sources are dynamic: new folder paths can be added, paused, resumed, or removed at any time without redeploying services.
- On first install, onboarding must ask for the local Obsidian vault path and persist it as a required connector setting.
- Qdrant deployment is selectable during onboarding:
  - default: managed local Qdrant container from our Docker Compose stack,
  - optional: user-provided external Qdrant URL + API key.
- Onboarding must ask where data should reside (local managed services vs external Qdrant) and configure connectors accordingly.
- Ingestion mode: cron-based background job every 5-10 minutes.
- Graph strategy: Obsidian remains source-of-truth for links; outbound links are mirrored into Qdrant metadata.
- Storage: Qdrant + Postgres.
- UI: FastAPI backend + Vue dashboard.
- Telemetry: Langfuse traces + token and cost tracking.
- Security: single-user local login + encrypted provider keys in Postgres.

## Success Criteria
- New/updated files are discovered and processed reliably on each cron cycle.
- Each file has trackable stage progress and error visibility.
- First-run onboarding captures Obsidian vault path and validates it before enabling ingestion.
- First-run onboarding supports both local Docker Qdrant and external Qdrant credentials.
- Extracted memory includes: project, problem, solution, date.
- Obsidian notes are auto-written with readable summaries and links.
- Qdrant contains searchable chunks with rich metadata filters and Obsidian link fields.
- Dashboard shows status, ingestion health, file progress, and token/cost telemetry.
- Chat answers use dual retrieval pipelines and return source citations.

## Target Architecture
1. `api` (FastAPI): auth, config, chat, status, metrics, file-progress APIs.
2. `worker` (FastAPI worker/service): cron orchestration, ingestion workflow execution.
3. `dashboard` (Vue): status page, file progress page, chat, connector settings, ontology review queue.
4. `postgres`: app state, jobs, ontology/taxonomy registry, pricing, secrets, progress logs.
5. `qdrant`: vector store + metadata payload.
6. `langfuse`: telemetry destination (cloud or self-hosted).

## Execution Phases

Detailed TODO documents for each phase are tracked in:
- `plan/PHASE_0_TODO.md`
- `plan/PHASE_0_1_TODO.md`
- `plan/PHASE_1_TODO.md`
- `plan/PHASE_2_TODO.md`
- `plan/PHASE_3_TODO.md`
- `plan/PHASE_4_TODO.md`
- `plan/PHASE_5_TODO.md`
- `plan/PHASE_6_TODO.md`

### Phase 0 - Project Bootstrap
- Create Docker Compose stack for API, worker, dashboard, Postgres, Qdrant.
- Add environment templates and service health checks.
- Add migration framework and baseline schema.
- Implement onboarding flow for data residency and connector setup.
- Add first-run validation for Obsidian vault path and Qdrant connection mode.

Deliverables:
- `docker-compose.yml`
- `.env.example`
- DB migration setup
- Onboarding API + UI screens for:
  - Obsidian vault path input/validation,
  - Qdrant mode selection (`local_docker` or `external`),
  - external Qdrant URL/API key capture and encryption.

### Phase 0.1 - First-Run Onboarding Gate
- Block ingestion and chat until onboarding is completed.
- Validate Obsidian vault path exists and is readable from worker runtime.
- If `local_docker` is selected, verify local Qdrant health check before completion.
- If `external` is selected, validate URL reachability and API key auth via test query.
- Persist connector config and onboarding completion timestamp in Postgres.

Deliverables:
- `onboarding_state` table and connector validation records
- Onboarding completion gate in API middleware and dashboard route guard
- Connector test endpoint used by onboarding UI

### Phase 1 - Ingestion Foundation
- Implement source registry for default paths + user-added paths.
- Support hot updates to source registry from the portal so cron picks up newly added local sources on the next run.
- Build incremental scanner with stable file fingerprint (`path + mtime + hash`).
- Implement cron scheduler (5-10 minute cadence).
- Record ingestion run metrics and per-file run records.

Deliverables:
- Source management APIs
- Source lifecycle controls (`active`, `paused`, `deleted`) with per-source health and last-scan timestamps
- Worker cron runner
- `ingestion_runs`, `ingested_files`, `file_processing_runs` tables

### Phase 2 - SimpleAgents YAML Pipelines (Core)
- Build YAML workflow for extraction:
  - normalize file
  - extract `project/problem/solution/date`
  - tag/entity classification
  - chunk + embed
  - Qdrant upsert
  - Obsidian summary write
  - telemetry emit
- Enforce strict output schemas for all `llm_call` nodes.
- Keep deterministic tasks in `custom_worker` nodes.

Deliverables:
- `workflows/ingest_memory_v1.yaml`
- Worker handlers for deterministic nodes
- Regression fixtures for extraction quality

### Phase 3 - Dynamic Ontology/Taxonomy Evolution
- Add ontology/taxonomy/relation registries in Postgres.
- Add agentic classification against existing registry.
- If no good match, auto-add provisional term/relation and push to review queue.
- Keep proposed entries immediately usable with `provisional=true`.

Deliverables:
- `ontology_terms`, `taxonomy_tags`, `relations`, `schema_proposals` tables
- `workflows/ontology_evolution_v1.yaml`
- Review queue APIs

### Phase 4 - Retrieval and Chat Orchestration
- Implement dual retrieval workflows:
  1) vector + metadata filter retrieval from Qdrant
  2) Obsidian outbound link-walk neighborhood retrieval
- Add synthesis workflow to generate final answer with citations.
- Include filters for project/date/tags/ontology.

Deliverables:
- `workflows/chat_vector_retrieval_v1.yaml`
- `workflows/chat_linkwalk_retrieval_v1.yaml`
- `workflows/chat_synthesis_v1.yaml`

### Phase 5 - Telemetry, Cost, and Status
- Emit SimpleAgents run telemetry to Langfuse (run, node, stage spans).
- Persist token usage events and compute costs from versioned model pricing table.
- Build status page metrics: job health, connector health, ingestion freshness, cost/tokens.

Deliverables:
- `model_pricing`, `token_usage_events` tables
- Langfuse integration module
- Status APIs + dashboard widgets

### Phase 6 - File-Level Progress and Reliability
- Track file stage machine:
  - `discovered -> parsed -> extracted -> ontology_mapped -> chunked -> embedded -> qdrant_upserted -> obsidian_written -> telemetry_emitted -> completed`
- Capture stage timestamps, durations, retries, and errors.
- Add retry queue with backoff for failed files.
- Add dashboard file timeline and live progress stream.

Deliverables:
- `file_stage_events`, `file_retry_queue` tables
- File progress APIs + SSE endpoint
- Dashboard file progress page and file detail panel

## Data Contracts (v1)

### Canonical Memory Record
- `record_id`
- `source_path`
- `source_type`
- `project`
- `problem`
- `solution`
- `event_date`
- `tags[]`
- `ontology_terms[]`
- `relation_hints[]`
- `confidence`
- `ingestion_run_id`

### Qdrant Payload
- `record_id`, `chunk_id`, `timestamp`
- `project`, `problem`, `solution`, `event_date`
- `tags[]`, `ontology_terms[]`
- `obsidian_note_path`
- `obsidian_wikilinks_out[]`
- `source_path`
- `provisional_terms[]`

## API Surface (v1)
- `POST /auth/login`
- `GET /onboarding/status`
- `POST /onboarding/configure`
- `GET /status/health`
- `GET /status/connectors`
- `GET /status/jobs`
- `GET /sources`
- `POST /sources`
- `PATCH /sources/{id}`
- `GET /runs/{run_id}/files`
- `GET /files/{file_id}/timeline`
- `POST /files/{file_id}/retry`
- `GET /metrics/costs`
- `GET /metrics/pipeline`
- `POST /chat/query`

## Security and Compliance
- Encrypt provider secrets before storing in Postgres (AES-GCM with master key from env/KMS).
- Never return raw stored secrets to UI after save.
- Mask secrets in logs and traces.
- Retention policy:
  - Raw source text: 90 days.
  - Structured memory and aggregates: retained indefinitely.

## Verification Plan
- Unit tests:
  - file fingerprinting
  - source scanner deduplication
  - stage transitions and retry policy
  - ontology proposal policy
- Integration tests:
  - end-to-end ingest to Qdrant and Obsidian
  - chat dual retrieval synthesis with citations
  - Langfuse event emission
- Load checks:
  - 5k-50k files batched ingestion benchmarks
  - cron overlap lock safety

## Risks and Mitigations
- Schema drift in source logs -> maintain per-source parsers with fallback raw capture.
- Ontology explosion -> confidence threshold + provisional review queue + merge tooling.
- Cost spikes -> provider budgets, model routing constraints, and run-level cost guardrails.
- Partial failures -> idempotent upserts, per-file retries, and stage checkpointing.

## Milestone Exit Checklist
- [ ] Docker stack starts and passes health checks.
- [ ] Cron ingestion runs on schedule and is idempotent.
- [ ] File-level progress is visible with retries.
- [ ] Dynamic ontology proposals flow into review queue.
- [ ] Obsidian summaries and links are written correctly.
- [ ] Qdrant retrieval + metadata filters return expected records.
- [ ] Chat combines vector and link-walk results with citations.
- [ ] Langfuse telemetry and token/cost dashboards are accurate.
