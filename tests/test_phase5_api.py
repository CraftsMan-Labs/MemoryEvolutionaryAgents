from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
import unittest
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient

from memory_evolutionary_agents.api import create_app
from memory_evolutionary_agents.container import AppContainer
from memory_evolutionary_agents.phase5.contracts import (
    ConnectorHealthItem,
    ConnectorHealthResponse,
    FreshnessStatusResponse,
    JobHealthResponse,
    UsageMetricsResponse,
    UsageTrendPoint,
)


class _FakeOnboarding:
    def is_completed(self) -> bool:
        return True


class _FakeStatusService:
    def job_health(self) -> JobHealthResponse:
        return JobHealthResponse(
            total_runs=10,
            running_runs=1,
            failed_runs=2,
            latest_run_id=20,
            latest_run_status="completed",
        )

    def connector_health(self) -> ConnectorHealthResponse:
        return ConnectorHealthResponse(
            total_sources=1,
            healthy_sources=1,
            unhealthy_sources=0,
            sources=[
                ConnectorHealthItem(
                    source_id=1,
                    source_path="/tmp/source",
                    state="active",
                    is_healthy=True,
                    last_error=None,
                    last_scan_at=None,
                )
            ],
        )

    def freshness(self) -> FreshnessStatusResponse:
        return FreshnessStatusResponse(
            latest_run_at=datetime(2026, 4, 3, tzinfo=timezone.utc),
            minutes_since_last_run=5,
            stale_threshold_minutes=30,
            is_stale=False,
        )

    def usage_metrics(self, range_days: int) -> UsageMetricsResponse:
        return UsageMetricsResponse(
            range_days=range_days,
            total_input_tokens=500,
            total_output_tokens=250,
            total_tokens=750,
            total_cost_amount=Decimal("0.120000"),
            currency="USD",
            trend=[
                UsageTrendPoint(
                    date="2026-04-03",
                    input_tokens=500,
                    output_tokens=250,
                    total_tokens=750,
                    cost_amount=Decimal("0.120000"),
                )
            ],
        )


def _container() -> AppContainer:
    return AppContainer(
        settings=cast(Any, None),
        database=cast(Any, None),
        source_registry=cast(Any, None),
        run_tracking=cast(Any, None),
        onboarding=cast(Any, _FakeOnboarding()),
        scanner=cast(Any, None),
        scheduler=cast(Any, None),
        phase2_ingestion=cast(Any, None),
        phase3_ontology=cast(Any, None),
        phase4_chat=cast(Any, None),
        phase5_telemetry=cast(Any, None),
        phase5_status=cast(Any, _FakeStatusService()),
        phase6_progress=cast(Any, None),
    )


class Phase5ApiTestCase(unittest.TestCase):
    def test_status_and_metrics_routes_return_typed_payloads(self) -> None:
        with patch(
            "memory_evolutionary_agents.api.build_container",
            return_value=_container(),
        ):
            client = TestClient(create_app())

            jobs = client.get("/status/jobs")
            self.assertEqual(jobs.status_code, 200)
            self.assertEqual(jobs.json()["failed_runs"], 2)

            connectors = client.get("/status/connectors")
            self.assertEqual(connectors.status_code, 200)
            self.assertEqual(connectors.json()["healthy_sources"], 1)

            freshness = client.get("/status/freshness")
            self.assertEqual(freshness.status_code, 200)
            self.assertEqual(freshness.json()["is_stale"], False)

            usage = client.get("/metrics/usage?days=14")
            self.assertEqual(usage.status_code, 200)
            self.assertEqual(usage.json()["range_days"], 14)


if __name__ == "__main__":
    unittest.main()
