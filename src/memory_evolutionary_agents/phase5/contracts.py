from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class TelemetryEventRequest(BaseModel):
    event_type: str = Field(min_length=1)
    run_id: int | None = None
    request_id: str | None = None
    correlation_id: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    status: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    error_classification: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    recorded_at: datetime


class ModelPricingRecord(BaseModel):
    id: int
    provider: str
    model_name: str
    currency: str
    input_cost_per_1k_tokens: Decimal
    output_cost_per_1k_tokens: Decimal
    effective_from: datetime
    effective_to: datetime | None


class TelemetryEventRecord(BaseModel):
    id: int
    event_type: str
    run_id: int | None
    request_id: str | None
    correlation_id: str
    stage: str
    status: str
    provider: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    pricing_version_id: int | None
    cost_amount: Decimal | None
    currency: str | None
    error_classification: str | None
    metadata: dict[str, object]
    recorded_at: datetime


class TelemetrySpanEvent(BaseModel):
    trace_id: str = Field(min_length=1)
    span_name: str = Field(min_length=1)
    span_kind: str = Field(min_length=1)
    status: str = Field(min_length=1)
    started_at: datetime
    ended_at: datetime
    metadata: dict[str, object] = Field(default_factory=dict)


class JobHealthResponse(BaseModel):
    total_runs: int
    running_runs: int
    failed_runs: int
    latest_run_id: int | None
    latest_run_status: str | None


class ConnectorHealthItem(BaseModel):
    source_id: int
    source_path: str
    state: str
    is_healthy: bool
    last_error: str | None
    last_scan_at: datetime | None


class ConnectorHealthResponse(BaseModel):
    total_sources: int
    healthy_sources: int
    unhealthy_sources: int
    sources: list[ConnectorHealthItem]


class FreshnessStatusResponse(BaseModel):
    latest_run_at: datetime | None
    minutes_since_last_run: int | None
    stale_threshold_minutes: int
    is_stale: bool


class UsageTrendPoint(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_amount: Decimal


class UsageMetricsResponse(BaseModel):
    range_days: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_amount: Decimal
    currency: str
    trend: list[UsageTrendPoint]


class ChunkTrendPoint(BaseModel):
    date: str
    chunks_created: int
    memories_created: int


class PipelineMetricsResponse(BaseModel):
    range_days: int
    total_runs: int
    total_memories: int
    total_chunks: int
    avg_chunks_per_memory: float
    trend: list[ChunkTrendPoint]
