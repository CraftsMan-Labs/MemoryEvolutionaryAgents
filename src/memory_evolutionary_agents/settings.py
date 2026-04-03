from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    db_path: str
    database_url: str | None
    scan_interval_seconds: int
    scan_cycle_timeout_seconds: int
    stage_timeout_seconds: int
    phase2_enabled: bool
    phase2_workflow_path: str
    workflow_provider: str
    workflow_api_base: str | None
    workflow_api_key: str | None
    workflow_model: str
    qdrant_url: str
    qdrant_api_key: str | None
    qdrant_collection: str
    obsidian_vault_path: str
    phase3_enabled: bool
    phase3_workflow_path: str
    phase3_match_threshold: float
    phase4_enabled: bool
    phase5_enabled: bool
    langfuse_enabled: bool
    langfuse_base_url: str | None
    langfuse_public_key: str | None
    langfuse_secret_key: str | None


def _load_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def load_settings() -> AppSettings:
    db_path = os.getenv("MEA_DB_PATH", "./memory_agents.db")
    database_url = os.getenv("MEA_DATABASE_URL")
    scan_interval_seconds_raw = os.getenv("MEA_SCAN_INTERVAL_SECONDS", "300")
    scan_cycle_timeout_seconds_raw = os.getenv("MEA_SCAN_CYCLE_TIMEOUT_SECONDS", "240")
    stage_timeout_seconds_raw = os.getenv("MEA_STAGE_TIMEOUT_SECONDS", "90")
    phase2_enabled = _load_bool(os.getenv("MEA_PHASE2_ENABLED"), default=False)
    phase2_workflow_path = os.getenv(
        "MEA_PHASE2_WORKFLOW_PATH", "./workflows/ingest_memory_v1.yaml"
    )
    workflow_provider = os.getenv("MEA_WORKFLOW_PROVIDER", "openai")
    workflow_api_base = os.getenv("MEA_WORKFLOW_API_BASE")
    workflow_api_key = os.getenv("MEA_WORKFLOW_API_KEY")
    workflow_model = os.getenv("MEA_WORKFLOW_MODEL", "gpt-4o-mini")
    qdrant_url = os.getenv("MEA_QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("MEA_QDRANT_API_KEY")
    qdrant_collection = os.getenv("MEA_QDRANT_COLLECTION", "memory_chunks")
    obsidian_vault_path = os.getenv("MEA_OBSIDIAN_VAULT_PATH", "./obsidian-vault")
    phase3_enabled = _load_bool(os.getenv("MEA_PHASE3_ENABLED"), default=False)
    phase3_workflow_path = os.getenv(
        "MEA_PHASE3_WORKFLOW_PATH", "./workflows/ontology_evolution_v1.yaml"
    )
    phase3_match_threshold_raw = os.getenv("MEA_PHASE3_MATCH_THRESHOLD", "0.82")
    phase4_enabled = _load_bool(os.getenv("MEA_PHASE4_ENABLED"), default=False)
    phase5_enabled = _load_bool(os.getenv("MEA_PHASE5_ENABLED"), default=False)
    langfuse_enabled = _load_bool(os.getenv("MEA_LANGFUSE_ENABLED"), default=False)
    langfuse_base_url = os.getenv("MEA_LANGFUSE_BASE_URL")
    langfuse_public_key = os.getenv("MEA_LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key = os.getenv("MEA_LANGFUSE_SECRET_KEY")
    scan_interval_seconds = int(scan_interval_seconds_raw)
    scan_cycle_timeout_seconds = int(scan_cycle_timeout_seconds_raw)
    stage_timeout_seconds = int(stage_timeout_seconds_raw)
    phase3_match_threshold = float(phase3_match_threshold_raw)
    if scan_interval_seconds < 60:
        raise ValueError("MEA_SCAN_INTERVAL_SECONDS must be >= 60")
    if scan_cycle_timeout_seconds < 30:
        raise ValueError("MEA_SCAN_CYCLE_TIMEOUT_SECONDS must be >= 30")
    if stage_timeout_seconds < 5:
        raise ValueError("MEA_STAGE_TIMEOUT_SECONDS must be >= 5")
    if phase2_enabled and database_url is None:
        raise ValueError("MEA_DATABASE_URL is required when MEA_PHASE2_ENABLED=true")
    if phase3_match_threshold < 0.0 or phase3_match_threshold > 1.0:
        raise ValueError("MEA_PHASE3_MATCH_THRESHOLD must be between 0.0 and 1.0")
    if phase3_enabled and database_url is None:
        raise ValueError("MEA_DATABASE_URL is required when MEA_PHASE3_ENABLED=true")
    if phase4_enabled and database_url is None:
        raise ValueError("MEA_DATABASE_URL is required when MEA_PHASE4_ENABLED=true")
    if phase5_enabled and database_url is None:
        raise ValueError("MEA_DATABASE_URL is required when MEA_PHASE5_ENABLED=true")
    return AppSettings(
        db_path=db_path,
        database_url=database_url,
        scan_interval_seconds=scan_interval_seconds,
        scan_cycle_timeout_seconds=scan_cycle_timeout_seconds,
        stage_timeout_seconds=stage_timeout_seconds,
        phase2_enabled=phase2_enabled,
        phase2_workflow_path=phase2_workflow_path,
        workflow_provider=workflow_provider,
        workflow_api_base=workflow_api_base,
        workflow_api_key=workflow_api_key,
        workflow_model=workflow_model,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        qdrant_collection=qdrant_collection,
        obsidian_vault_path=obsidian_vault_path,
        phase3_enabled=phase3_enabled,
        phase3_workflow_path=phase3_workflow_path,
        phase3_match_threshold=phase3_match_threshold,
        phase4_enabled=phase4_enabled,
        phase5_enabled=phase5_enabled,
        langfuse_enabled=langfuse_enabled,
        langfuse_base_url=langfuse_base_url,
        langfuse_public_key=langfuse_public_key,
        langfuse_secret_key=langfuse_secret_key,
    )
