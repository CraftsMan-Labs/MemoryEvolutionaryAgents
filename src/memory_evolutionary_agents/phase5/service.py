from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from ..run_tracking import RunTrackingService
from ..source_registry import SourceRegistryService
from .adapters import TelemetryAdapter
from .contracts import (
    ConnectorHealthItem,
    ConnectorHealthResponse,
    FreshnessStatusResponse,
    JobHealthResponse,
    PipelineMetricsResponse,
    TelemetryEventRecord,
    TelemetryEventRequest,
    TelemetrySpanEvent,
    UsageMetricsResponse,
)
from .costing import CostCalculatorService
from .errors import TelemetryAdapterError
from .persistence import TelemetryRepository


class TelemetryService:
    def __init__(
        self,
        telemetry_repository: TelemetryRepository,
        cost_calculator: CostCalculatorService,
        adapter: TelemetryAdapter,
    ) -> None:
        self._telemetry_repository = telemetry_repository
        self._cost_calculator = cost_calculator
        self._adapter = adapter

    def record_event(
        self,
        request: TelemetryEventRequest,
        span_name: str,
        span_kind: str,
        allow_missing_pricing: bool = True,
    ) -> TelemetryEventRecord:
        cost = self._cost_calculator.compute_cost(
            request=request,
            allow_missing_pricing=allow_missing_pricing,
        )
        persisted = self._telemetry_repository.insert_event(
            request=request,
            pricing_version_id=cost.pricing.id if cost.pricing is not None else None,
            cost_amount=cost.cost_amount,
            currency=cost.currency,
        )
        self._emit_span(
            trace_id=request.correlation_id,
            span_name=span_name,
            span_kind=span_kind,
            status=request.status,
            metadata={
                "event_type": request.event_type,
                "run_id": request.run_id,
                "request_id": request.request_id,
                "stage": request.stage,
                "provider": request.provider,
                "model_name": request.model_name,
                "input_tokens": request.input_tokens,
                "output_tokens": request.output_tokens,
                "cost_amount": str(cost.cost_amount)
                if cost.cost_amount is not None
                else None,
                **request.metadata,
            },
            at=request.recorded_at,
        )
        return persisted

    def classify_failure(self, error: Exception) -> str:
        name = error.__class__.__name__.lower()
        if "timeout" in name:
            return "timeout"
        if "validation" in name:
            return "validation"
        if "auth" in name or "permission" in name:
            return "auth"
        return "runtime"

    def _emit_span(
        self,
        trace_id: str,
        span_name: str,
        span_kind: str,
        status: str,
        metadata: dict[str, object],
        at: datetime,
    ) -> None:
        event = TelemetrySpanEvent(
            trace_id=trace_id,
            span_name=span_name,
            span_kind=span_kind,
            status=status,
            started_at=at,
            ended_at=at,
            metadata=metadata,
        )
        try:
            self._adapter.emit_span(event)
        except TelemetryAdapterError:
            return


class Phase5StatusService:
    def __init__(
        self,
        run_tracking: RunTrackingService,
        source_registry: SourceRegistryService,
        telemetry_repository: TelemetryRepository,
    ) -> None:
        self._run_tracking = run_tracking
        self._source_registry = source_registry
        self._telemetry_repository = telemetry_repository

    def job_health(self) -> JobHealthResponse:
        runs = self._run_tracking.list_runs(limit=50)
        running_runs = len([run for run in runs if run.status == "running"])
        failed_runs = len([run for run in runs if run.status == "failed"])
        latest = runs[0] if len(runs) > 0 else None
        return JobHealthResponse(
            total_runs=len(runs),
            running_runs=running_runs,
            failed_runs=failed_runs,
            latest_run_id=latest.id if latest is not None else None,
            latest_run_status=latest.status if latest is not None else None,
        )

    def connector_health(self) -> ConnectorHealthResponse:
        sources = self._source_registry.list_sources()
        items: list[ConnectorHealthItem] = []
        for source in sources:
            is_healthy = source.state.value == "active" and source.last_error is None
            items.append(
                ConnectorHealthItem(
                    source_id=source.id,
                    source_path=source.path,
                    state=source.state.value,
                    is_healthy=is_healthy,
                    last_error=source.last_error,
                    last_scan_at=source.last_scan_at,
                )
            )
        healthy = len([item for item in items if item.is_healthy])
        return ConnectorHealthResponse(
            total_sources=len(items),
            healthy_sources=healthy,
            unhealthy_sources=len(items) - healthy,
            sources=items,
        )

    def freshness(self, stale_threshold_minutes: int = 30) -> FreshnessStatusResponse:
        runs = self._run_tracking.list_runs(limit=1)
        latest_run_at = runs[0].ended_at if len(runs) > 0 else None
        if latest_run_at is None:
            return FreshnessStatusResponse(
                latest_run_at=None,
                minutes_since_last_run=None,
                stale_threshold_minutes=stale_threshold_minutes,
                is_stale=True,
            )
        now = datetime.now(tz=timezone.utc)
        delta_seconds = (now - latest_run_at).total_seconds()
        elapsed_minutes = int(delta_seconds // 60)
        return FreshnessStatusResponse(
            latest_run_at=latest_run_at,
            minutes_since_last_run=elapsed_minutes,
            stale_threshold_minutes=stale_threshold_minutes,
            is_stale=elapsed_minutes > stale_threshold_minutes,
        )

    def usage_metrics(self, range_days: int = 7) -> UsageMetricsResponse:
        trend = self._telemetry_repository.usage_trend(range_days=range_days)
        total_input = sum(item.input_tokens for item in trend)
        total_output = sum(item.output_tokens for item in trend)
        total_tokens = sum(item.total_tokens for item in trend)
        total_cost = sum((item.cost_amount for item in trend), Decimal("0"))
        return UsageMetricsResponse(
            range_days=range_days,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tokens,
            total_cost_amount=total_cost,
            currency="USD",
            trend=trend,
        )

    def pipeline_metrics(self, range_days: int = 7) -> PipelineMetricsResponse:
        trend = self._telemetry_repository.chunk_creation_trend(range_days=range_days)
        total_memories, total_chunks = self._telemetry_repository.memory_chunk_totals()
        total_runs = len(self._run_tracking.list_runs(limit=200))
        avg_chunks_per_memory = 0.0
        if total_memories > 0:
            avg_chunks_per_memory = float(total_chunks) / float(total_memories)
        return PipelineMetricsResponse(
            range_days=range_days,
            total_runs=total_runs,
            total_memories=total_memories,
            total_chunks=total_chunks,
            avg_chunks_per_memory=avg_chunks_per_memory,
            trend=trend,
        )
