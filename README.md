# MemoryEvolutionaryAgents

Phase 1 foundation includes source registry APIs, incremental scanner, cron-style run orchestration, and per-file ingestion tracking.

## Architecture Diagram

```mermaid
flowchart TB
    subgraph Sources[Local Sources]
        C1[~/.claude]
        C2[~/.codex]
        C3[~/.opencode]
        C4[User-added folders]
    end

    subgraph Portal[Vue Dashboard]
        P0[Onboarding Wizard]
        P1[Chat]
        P2[Status]
        P3[File Progress]
        P4[Ontology Review Queue]
        P5[Connectors and API Keys]
    end

    subgraph API[FastAPI Service]
        A1[Auth]
        A0[Onboarding and Connector Config API]
        A2[Source Registry API]
        A3[Chat Orchestrator API]
        A4[Metrics and Status API]
        A5[File Progress API]
    end

    SR[(Postgres Source Registry)]

    subgraph Worker[Background Worker]
        W1[Cron Scheduler 5-10 min]
        W2[Incremental Scanner]
        W3[SimpleAgents YAML Orchestrator]
        W4[File Stage Tracker]
        W5[Telemetry Emitter]
    end

    subgraph Workflows[SimpleAgents YAML Pipelines]
        Y1[Ingest and Normalize]
        Y2[Extract project/problem/solution/date]
        Y3[Ontology/Taxonomy Classify]
        Y4[Propose New Terms]
        Y5[Chunk and Embed]
        Y6[Qdrant Upsert]
        Y7[Obsidian Summary Write]
        Y8[Dual Retrieval Chat]
        Y9[Final Synthesis with Citations]
    end

    subgraph Data[State and Memory]
        D1[(Postgres)]
        D2[(Qdrant Local Docker)]
        D5[(Qdrant External)]
        D3[Obsidian Vault]
        D4[Langfuse]
    end

    C1 --> W2
    C2 --> W2
    C3 --> W2
    C4 --> W2

    Portal --> A2
    Portal --> A0
    A0 --> D1
    A2 --> SR
    SR --> W2

    W1 --> W2 --> W3
    W3 --> Y1 --> Y2 --> Y3 --> Y4 --> Y5 --> Y6
    Y3 --> D1
    Y4 --> D1
    Y6 --> D2
    Y6 --> D5
    Y7 --> D3
    W4 --> D1
    W5 --> D4

    Portal --> API
    API --> D1
    API --> D2
    API --> D5
    API --> D3
    API --> D4

    API --> Y8
    Y8 --> D2
    Y8 --> D5
    Y8 --> D3
    Y8 --> Y9
    Y9 --> API
```

## Onboarding and Data Residency

```mermaid
sequenceDiagram
    participant U as User
    participant P as Onboarding Wizard
    participant A as FastAPI Onboarding API
    participant PG as Postgres
    participant Q as Qdrant Target

    U->>P: Enter Obsidian vault path
    P->>A: Submit vault path + qdrant mode
    A->>A: Validate vault path
    alt local_docker
        A->>Q: Check local Qdrant health
    else external
        P->>A: Submit external URL + API key
        A->>Q: Test external Qdrant auth/query
    end
    A->>PG: Save connector config (encrypted secrets)
    A->>PG: Mark onboarding completed
    A-->>P: Return success and enable app
```

## Runtime Flow (Ingestion)

```mermaid
sequenceDiagram
    participant Cron as Cron Scheduler
    participant Scan as Incremental Scanner
    participant SA as SimpleAgents Workflow
    participant PG as Postgres
    participant QD as Qdrant
    participant OB as Obsidian
    participant LF as Langfuse

    Cron->>Scan: trigger every 5-10 minutes
    Scan->>PG: load source registry and cursors
    Scan->>Scan: detect new/changed files
    loop each file
        Scan->>PG: create file_processing_run (discovered)
        Scan->>SA: run ingest_memory_v1
        SA->>PG: save extracted structured memory
        SA->>PG: update ontology/taxonomy and proposals
        SA->>QD: upsert chunks + metadata + obsidian_wikilinks_out
        SA->>OB: write/update human-readable summary note
        SA->>PG: append stage events and mark status
        SA->>LF: emit run and node telemetry
    end
    SA->>PG: finalize ingestion_run metrics
```

## File Processing State Machine

```mermaid
stateDiagram-v2
    [*] --> discovered
    discovered --> parsed
    parsed --> extracted
    extracted --> ontology_mapped
    ontology_mapped --> chunked
    chunked --> embedded
    embedded --> qdrant_upserted
    qdrant_upserted --> obsidian_written
    obsidian_written --> telemetry_emitted
    telemetry_emitted --> completed

    discovered --> failed
    parsed --> failed
    extracted --> failed
    ontology_mapped --> failed
    chunked --> failed
    embedded --> failed
    qdrant_upserted --> failed
    obsidian_written --> failed
    telemetry_emitted --> failed

    failed --> retry_queued
    retry_queued --> discovered
```

## Chat Retrieval Orchestration

```mermaid
flowchart LR
    U[User Query] --> O[Chat Orchestrator]
    O --> V[Pipeline A: Qdrant Vector + Metadata Filters]
    O --> L[Pipeline B: Obsidian Link Walk]
    V --> S[Final Synthesis Node]
    L --> S
    S --> R[Answer + Citations + Confidence]
```

## Docker Bootstrap (Phase 0)

```bash
cp .env.example .env
docker compose up --build
```

Or via `make` shortcuts:

```bash
make rebuild
```

Services:
- API: `http://localhost:8000`
- Dashboard: `http://localhost:5173`
- Qdrant: `http://localhost:6333`
- Postgres: `localhost:5432`

Useful make targets:
- `make up`
- `make down`
- `make build`
- `make rebuild`
- `make migrate`
- `make logs`

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
- `MEA_STAGE_TIMEOUT_SECONDS`: per-stage workflow timeout in seconds (default `90`, min `5`)
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
- `MEA_EMBEDDING_PROVIDER`: embedding provider (`deterministic` or `ollama`)
- `MEA_EMBEDDING_API_BASE`: embedding API base (for Ollama, e.g. `http://host.docker.internal:11434`)
- `MEA_EMBEDDING_MODEL`: embedding model identifier (for Ollama, e.g. `nomic-embed-text-v2-moe:latest`)
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
- `GET /files/{file_id}/timeline`
- `POST /files/{file_id}/retry`
- `GET /runs/{run_id}/stream`
- `GET /status/dead-letter`
- `GET /ontology/proposals`
- `GET /ontology/proposals/{proposal_id}`
- `POST /ontology/proposals/{proposal_id}/approve`
- `POST /ontology/proposals/{proposal_id}/reject`
- `POST /ontology/proposals/{proposal_id}/merge`
- `POST /chat/query`
