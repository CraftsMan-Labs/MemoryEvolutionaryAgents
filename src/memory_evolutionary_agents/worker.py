from __future__ import annotations

import time
from datetime import datetime, timezone
import signal

from .container import AppContainer, build_container
from .phase2.errors import WorkflowExecutionError
from .phase5.contracts import TelemetryEventRequest


def run_once() -> None:
    container = build_container()
    if container.onboarding.is_completed() is False:
        return
    _process_due_retries(container)
    started_at = datetime.now(tz=timezone.utc)
    cycle = container.scheduler.run_cycle()
    _record_run_telemetry(
        container=container,
        run_id=cycle.run.id,
        stage="scan_cycle",
        status="success",
        recorded_at=started_at,
    )
    if container.phase2_ingestion is not None:
        container.phase2_ingestion.execute_for_run(cycle.run.id)


def run_forever() -> None:
    container = build_container()
    stop_requested = False

    def _request_stop(*_: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        container.scheduler.request_stop()

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    while True:
        if stop_requested:
            break
        if container.onboarding.is_completed() is False:
            time.sleep(container.settings.scan_interval_seconds)
            continue
        _process_due_retries(container)
        started_at = datetime.now(tz=timezone.utc)
        cycle = container.scheduler.run_cycle()
        _record_run_telemetry(
            container=container,
            run_id=cycle.run.id,
            stage="scan_cycle",
            status="success",
            recorded_at=started_at,
        )
        if container.phase2_ingestion is not None:
            container.phase2_ingestion.execute_for_run(cycle.run.id)
        time.sleep(container.settings.scan_interval_seconds)


def _record_run_telemetry(
    container: AppContainer,
    run_id: int,
    stage: str,
    status: str,
    recorded_at: datetime,
) -> None:
    if container.phase5_telemetry is None:
        return
    container.phase5_telemetry.record_event(
        request=TelemetryEventRequest(
            event_type="ingest_run",
            run_id=run_id,
            request_id=None,
            correlation_id=f"run-{run_id}",
            stage=stage,
            status=status,
            provider="system",
            model_name="scheduler",
            input_tokens=0,
            output_tokens=0,
            error_classification=None,
            metadata={},
            recorded_at=recorded_at,
        ),
        span_name="worker.scan_cycle",
        span_kind="run",
        allow_missing_pricing=True,
    )


def _process_due_retries(container: AppContainer) -> None:
    if container.phase2_ingestion is None:
        return
    due = container.phase6_progress.next_due_retries(limit=100)
    for item in due:
        try:
            container.phase6_progress.begin_retry(item)
            container.phase2_ingestion.execute_file_run(item.file_run_id)
            latest = container.run_tracking.get_file_run(item.file_run_id)
            container.phase6_progress.settle_retry(item.file_run_id, latest.stage)
        except (RuntimeError, ValueError, OSError, WorkflowExecutionError) as exc:
            container.phase6_progress.fail_retry(item, exc)


if __name__ == "__main__":
    run_forever()
