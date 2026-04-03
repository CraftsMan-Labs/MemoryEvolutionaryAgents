from __future__ import annotations

import os
from pathlib import Path
import unittest
from typing import Any, cast
from datetime import datetime, timezone

from psycopg import Connection

from memory_evolutionary_agents.phase2.persistence import PostgresConnectionFactory
from memory_evolutionary_agents.phase5.adapters import NoopTelemetryAdapter
from memory_evolutionary_agents.phase5.contracts import TelemetryEventRequest
from memory_evolutionary_agents.phase5.costing import CostCalculatorService
from memory_evolutionary_agents.phase5.persistence import (
    PricingRepository,
    TelemetryRepository,
)
from memory_evolutionary_agents.phase5.service import TelemetryService


class Phase5IntegrationTestCase(unittest.TestCase):
    def test_ingest_and_chat_telemetry_persist_and_aggregate(self) -> None:
        if os.getenv("MEA_RUN_INTEGRATION_TESTS", "0") != "1":
            self.skipTest("Set MEA_RUN_INTEGRATION_TESTS=1 to run integration test")

        database_url = os.getenv(
            "MEA_INTEGRATION_DATABASE_URL",
            "postgresql://memory_agents:memory_agents@127.0.0.1:5434/memory_agents_test",
        )
        self._prepare_tables(database_url)

        connection_factory = PostgresConnectionFactory(database_url)
        telemetry_repository = TelemetryRepository(connection_factory)
        pricing_repository = PricingRepository(connection_factory)
        service = TelemetryService(
            telemetry_repository=telemetry_repository,
            cost_calculator=CostCalculatorService(pricing_repository),
            adapter=NoopTelemetryAdapter(),
        )

        now = datetime.now(tz=timezone.utc)
        service.record_event(
            request=TelemetryEventRequest(
                event_type="ingest_node",
                run_id=7,
                request_id=None,
                correlation_id="run-7-file-1",
                stage="workflow_completed",
                status="success",
                provider="openai",
                model_name="gpt-4o-mini",
                input_tokens=120,
                output_tokens=60,
                error_classification=None,
                metadata={"file_path": "/tmp/a.md"},
                recorded_at=now,
            ),
            span_name="ingest.workflow_completed",
            span_kind="node",
            allow_missing_pricing=False,
        )
        service.record_event(
            request=TelemetryEventRequest(
                event_type="chat_request",
                run_id=None,
                request_id="chat-1",
                correlation_id="chat-chat-1",
                stage="synthesis",
                status="success",
                provider="openai",
                model_name="gpt-4o-mini",
                input_tokens=80,
                output_tokens=40,
                error_classification=None,
                metadata={"vector_kept": 2},
                recorded_at=now,
            ),
            span_name="chat.synthesis",
            span_kind="node",
            allow_missing_pricing=False,
        )

        trend = telemetry_repository.usage_trend(range_days=1)
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0].input_tokens, 200)
        self.assertEqual(trend[0].output_tokens, 100)
        self.assertEqual(trend[0].total_tokens, 300)

    def _prepare_tables(self, database_url: str) -> None:
        root = Path(__file__).resolve().parents[1]
        phase2_sql = (root / "migrations/004_phase2_ingestion_core.sql").read_text(
            encoding="utf-8"
        )
        phase3_sql = (root / "migrations/005_phase3_ontology_evolution.sql").read_text(
            encoding="utf-8"
        )
        phase5_sql = (
            root / "migrations/006_phase5_telemetry_cost_status.sql"
        ).read_text(encoding="utf-8")
        with Connection.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(cast(Any, phase2_sql))
                cur.execute(cast(Any, phase3_sql))
                cur.execute(cast(Any, phase5_sql))
                cur.execute(cast(Any, "TRUNCATE TABLE token_usage_events CASCADE"))
                cur.execute(cast(Any, "TRUNCATE TABLE model_pricing CASCADE"))
                cur.execute(
                    cast(
                        Any,
                        """
                        INSERT INTO model_pricing(
                          provider,
                          model_name,
                          currency,
                          input_cost_per_1k_tokens,
                          output_cost_per_1k_tokens,
                          effective_from,
                          effective_to
                        ) VALUES ('openai', 'gpt-4o-mini', 'USD', 0.15, 0.60, NOW() - INTERVAL '1 day', NULL)
                        """,
                    )
                )
            conn.commit()


if __name__ == "__main__":
    unittest.main()
