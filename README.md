# MemoryEvolutionaryAgents

Phase 1 foundation includes source registry APIs, incremental scanner, cron-style run orchestration, and per-file ingestion tracking.

## Docker Bootstrap (Phase 0)

```bash
cp .env.example .env
docker compose up --build
```

Services:
- API: `http://localhost:8000`
- Dashboard: `http://localhost:5173`
- Qdrant: `http://localhost:6333`
- Postgres: `localhost:5432`

## Quick Start

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
uvicorn memory_evolutionary_agents.api:create_app --factory --reload
```

## Worker Commands

```bash
uv run python -m memory_evolutionary_agents.worker
```

## Frontend Tooling

- Use `bun` for Vue package management, scripts, and local dev.
- Preferred commands:
  - `bun install`
  - `bun run dev`
  - `bun run test`
  - `bun run build`

## Environment Variables

- `MEA_DB_PATH`: sqlite path for local development (default `./memory_agents.db`)
- `MEA_SCAN_INTERVAL_SECONDS`: scan cadence in seconds (default `300`, min `60`)
- `MEA_SCAN_CYCLE_TIMEOUT_SECONDS`: max scan-cycle execution budget (default `240`, min `30`)
- `MEA_MASTER_KEY`: Fernet-compatible key used to encrypt connector secrets at rest
- `MEA_DATABASE_URL`: Postgres DSN used for Phase 2 canonical memory persistence
- `MEA_PHASE2_ENABLED`: enables Phase 2 YAML workflow ingestion execution (`true`/`false`)
- `MEA_PHASE2_WORKFLOW_PATH`: workflow file path (default `./workflows/ingest_memory_v1.yaml`)
- `MEA_PHASE3_ENABLED`: enables Phase 3 ontology evolution and proposal queue (`true`/`false`)
- `MEA_PHASE3_WORKFLOW_PATH`: workflow file path (default `./workflows/ontology_evolution_v1.yaml`)
- `MEA_PHASE3_MATCH_THRESHOLD`: deterministic reuse threshold for ontology/tag matching (default `0.82`)
- `MEA_PHASE4_ENABLED`: enables Phase 4 dual retrieval chat orchestration (`true`/`false`)
- `MEA_WORKFLOW_PROVIDER`: provider used by `simple-agents-py` workflow runtime
- `MEA_WORKFLOW_API_BASE`: provider API base URL
- `MEA_WORKFLOW_API_KEY`: provider API key for workflow execution
- `MEA_WORKFLOW_MODEL`: default model identifier for workflow execution
- `MEA_QDRANT_URL`: Qdrant endpoint used by Phase 2 adapters
- `MEA_QDRANT_API_KEY`: optional Qdrant API key
- `MEA_QDRANT_COLLECTION`: Qdrant collection for memory chunk vectors
- `MEA_OBSIDIAN_VAULT_PATH`: filesystem path used by the Obsidian summary adapter

## Phase 2 Workflow Assets

- Workflow YAML: `workflows/ingest_memory_v1.yaml`
- Deterministic handler bridge: `src/memory_evolutionary_agents/phase2/workflow_handlers.py`
- Postgres persistence schema: `migrations/004_phase2_ingestion_core.sql`

## Phase 3 Workflow Assets

- Workflow YAML: `workflows/ontology_evolution_v1.yaml`
- Ontology evolution service: `src/memory_evolutionary_agents/phase3/service.py`
- Postgres persistence schema: `migrations/005_phase3_ontology_evolution.sql`

## Phase 4 Workflow Assets

- Workflow YAML: `workflows/chat_vector_retrieval_v1.yaml`
- Workflow YAML: `workflows/chat_linkwalk_retrieval_v1.yaml`
- Workflow YAML: `workflows/chat_synthesis_v1.yaml`
- Chat orchestration service: `src/memory_evolutionary_agents/phase4/service.py`

## Phase 2 Local Integration Test Stack

Start local Postgres + Qdrant for integration tests:

```bash
docker compose -f docker-compose.integration.yml up -d --wait
```

Run integration tests directly:

```bash
MEA_RUN_INTEGRATION_TESTS=1 \
MEA_INTEGRATION_DATABASE_URL=postgresql://memory_agents:memory_agents@127.0.0.1:5434/memory_agents_test \
MEA_INTEGRATION_QDRANT_URL=http://127.0.0.1:6334 \
uv run python -m unittest tests.test_phase2_integration tests.test_phase3_integration tests.test_phase4_integration
```

Or use the helper script (boot + run + teardown):

```bash
./scripts/run_phase2_integration_tests.sh
```

## Implemented Endpoints (Phase 0.1 + Phase 1)

Onboarding routes (always available):

- `GET /onboarding/status`
- `POST /onboarding/test-connector`
- `POST /onboarding/configure`

After onboarding is completed, protected routes are available:

- `GET /status/health`
- `GET /sources`
- `POST /sources`
- `PATCH /sources/{source_id}`
- `GET /status/jobs`
- `POST /jobs/scan`
- `GET /runs/{run_id}/files`
- `GET /ontology/proposals`
- `GET /ontology/proposals/{proposal_id}`
- `POST /ontology/proposals/{proposal_id}/approve`
- `POST /ontology/proposals/{proposal_id}/reject`
- `POST /ontology/proposals/{proposal_id}/merge`
- `POST /chat/query`
