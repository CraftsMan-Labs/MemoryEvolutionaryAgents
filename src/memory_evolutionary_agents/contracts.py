from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator


class SourceState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


class QdrantMode(str, Enum):
    LOCAL_DOCKER = "local_docker"
    EXTERNAL = "external"


class SourceCreateRequest(BaseModel):
    path: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if Path(value).expanduser().exists() is False:
            raise ValueError("source path does not exist")
        return str(Path(value).expanduser().resolve())


class SourcePatchRequest(BaseModel):
    state: SourceState | None = None
    path: str | None = None

    @field_validator("path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        expanded = Path(value).expanduser()
        if expanded.exists() is False:
            raise ValueError("source path does not exist")
        return str(expanded.resolve())


class SourceRecord(BaseModel):
    id: int
    path: str
    state: SourceState
    created_at: datetime
    updated_at: datetime
    last_scan_at: datetime | None
    last_error: str | None
    last_scan_file_count: int
    last_scan_error_count: int


class IngestionRunRecord(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None
    status: str
    total_discovered: int
    total_queued: int
    total_failed: int


class FileRunRecord(BaseModel):
    id: int
    run_id: int
    source_id: int
    source_path: str
    file_path: str
    stage: str
    status: str
    error_code: str | None
    error_message: str | None
    created_at: datetime


class RunSummaryResponse(BaseModel):
    run: IngestionRunRecord
    files: list[FileRunRecord]


class OnboardingConfigureRequest(BaseModel):
    obsidian_vault_path: str = Field(min_length=1)
    qdrant_mode: QdrantMode
    external_qdrant_url: str | None = None
    external_qdrant_api_key: str | None = None

    @field_validator("obsidian_vault_path")
    @classmethod
    def validate_obsidian_path(cls, value: str) -> str:
        expanded = Path(value).expanduser()
        if expanded.exists() is False:
            raise ValueError("obsidian vault path does not exist")
        if expanded.is_dir() is False:
            raise ValueError("obsidian vault path must be a directory")
        return str(expanded.resolve())

    @field_validator("external_qdrant_url")
    @classmethod
    def validate_external_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if (
            value.startswith("http://") is False
            and value.startswith("https://") is False
        ):
            raise ValueError("external qdrant url must start with http:// or https://")
        return value.rstrip("/")


class OnboardingStatusResponse(BaseModel):
    is_completed: bool
    completed_at: datetime | None
    qdrant_mode: QdrantMode | None
    obsidian_vault_path: str | None
    external_qdrant_url: str | None
    has_external_qdrant_api_key: bool
    block_reason: str | None


class OnboardingConfigureResponse(BaseModel):
    is_completed: bool
    completed_at: datetime
    qdrant_mode: QdrantMode


class ConnectorTestRequest(BaseModel):
    qdrant_mode: QdrantMode
    obsidian_vault_path: str
    external_qdrant_url: str | None = None
    external_qdrant_api_key: str | None = None


class ConnectorTestResponse(BaseModel):
    obsidian_ok: bool
    qdrant_ok: bool
    message: str


class ConnectorConfigRecord(BaseModel):
    id: int
    obsidian_vault_path: str
    qdrant_mode: QdrantMode
    external_qdrant_url: str | None
    external_qdrant_api_key_encrypted: str | None
    created_at: datetime
    updated_at: datetime


class OnboardingStateRecord(BaseModel):
    id: int
    is_completed: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ValidationResult(BaseModel):
    is_valid: bool
    message: str


@dataclass(frozen=True)
class FileSnapshot:
    source_id: int
    source_path: str
    file_path: str
    mtime_ns: int
    content_hash: str
    fingerprint: str
