from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FileStage(str, Enum):
    DISCOVERED = "discovered"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_QUEUED = "retry_queued"
    RETRYING = "retrying"
    POISONED = "poisoned"


class StageTransitionRequest(BaseModel):
    run_id: int
    file_run_id: int
    source_id: int
    file_path: str = Field(min_length=1)
    to_stage: FileStage
    status: str = Field(min_length=1)
    error_code: str | None = None
    error_message: str | None = None
    occurred_at: datetime


class FileProgressRecord(BaseModel):
    file_run_id: int
    run_id: int
    source_id: int
    source_path: str
    file_path: str
    stage: FileStage
    status: str
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime | None = None


class FileStageSummary(BaseModel):
    stage: FileStage
    total: int


class FileStatusSummary(BaseModel):
    status: str
    total: int


class RunFilesQuery(BaseModel):
    source_id: int | None = None
    stage: FileStage | None = None
    status: str | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    limit: int = Field(default=200, ge=1, le=2000)


class RunFilesResponse(BaseModel):
    run_id: int
    files: list[FileProgressRecord]
    stage_summary: list[FileStageSummary]
    status_summary: list[FileStatusSummary]


class FileTimelineEvent(BaseModel):
    id: int
    run_id: int
    file_run_id: int
    source_id: int
    file_path: str
    from_stage: FileStage | None
    to_stage: FileStage
    status: str
    duration_ms: int | None
    error_code: str | None
    error_message: str | None
    recorded_at: datetime


class FileTimelineResponse(BaseModel):
    file_run_id: int
    events: list[FileTimelineEvent]


class RetryQueueRecord(BaseModel):
    id: int
    file_run_id: int
    run_id: int
    source_id: int
    file_path: str
    status: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime
    last_error_code: str | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime


class RetryScheduleResult(BaseModel):
    file_run_id: int
    attempt_count: int
    next_attempt_at: datetime
    status: str


class FileRetryRequest(BaseModel):
    requested_by: str = Field(min_length=1)
