# Memory Evolutionary Agents - Architecture

This document defines the v1 system architecture for ingesting local agent session data, evolving memory schemas, and serving searchable memory through Qdrant, Obsidian, and a web portal.

## System Overview

```mermaid
flowchart TB
    subgraph Sources[Local Sources]
        C1[~/.claude]
        C2[~/.codex]
        C3[~/.opencode]
        C4[User-added folders]
    end

    subgraph Portal[Vue Dashboard]
        P1[Chat]
        P2[Status]
        P3[File Progress]
        P4[Ontology Review Queue]
        P5[Connectors and API Keys]
    end

    subgraph API[FastAPI Service]
        A1[Auth]
        A2[Source Registry API]
        A3[Chat Orchestrator API]
        A4[Metrics and Status API]
        A5[File Progress API]
    end

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
        D2[(Qdrant)]
        D3[Obsidian Vault]
        D4[Langfuse]
    end

    C1 --> W2
    C2 --> W2
    C3 --> W2
    C4 --> W2

    W1 --> W2 --> W3
    W3 --> Y1 --> Y2 --> Y3 --> Y4 --> Y5 --> Y6
    Y3 --> D1
    Y4 --> D1
    Y6 --> D2
    Y7 --> D3
    W4 --> D1
    W5 --> D4

    Portal --> API
    API --> D1
    API --> D2
    API --> D3
    API --> D4

    API --> Y8
    Y8 --> D2
    Y8 --> D3
    Y8 --> Y9
    Y9 --> API
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

## Service Boundaries

- `FastAPI API`: authentication, source configuration, chat APIs, metrics and status endpoints.
- `Worker`: cron jobs, workflow execution, retries, stage tracking, and telemetry emission.
- `Postgres`: source registry, run history, file progress, ontology/taxonomy/relation registry, model pricing, encrypted connector secrets.
- `Qdrant`: vector search and metadata filtering with mirrored Obsidian link fields.
- `Obsidian Vault`: human-readable memory notes and wikilink graph.
- `Langfuse`: trace-level observability and token-cost telemetry correlation.
