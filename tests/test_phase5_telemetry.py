from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from memory_evolutionary_agents.phase5.adapters import TelemetryAdapter
from memory_evolutionary_agents.phase5.contracts import (
    ModelPricingRecord,
    TelemetryEventRecord,
    TelemetryEventRequest,
)
from memory_evolutionary_agents.phase5.costing import CostCalculatorService
from memory_evolutionary_agents.phase5.persistence import (
    PricingRepository,
    TelemetryRepository,
)
from memory_evolutionary_agents.phase5.service import TelemetryService


class _FakePricingRepository(PricingRepository):
    def __init__(self, record: ModelPricingRecord | None) -> None:
        self._record = record

    def find_effective_pricing(self, provider: str, model_name: str, at_time: datetime):
        _ = (provider, model_name, at_time)
        return self._record


class _FakeTelemetryRepository(TelemetryRepository):
    def __init__(self) -> None:
        self.events: list[TelemetryEventRecord] = []

    def insert_event(self, request, pricing_version_id, cost_amount, currency):
        record = TelemetryEventRecord(
            id=len(self.events) + 1,
            event_type=request.event_type,
            run_id=request.run_id,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            stage=request.stage,
            status=request.status,
            provider=request.provider,
            model_name=request.model_name,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            total_tokens=request.input_tokens + request.output_tokens,
            pricing_version_id=pricing_version_id,
            cost_amount=cost_amount,
            currency=currency,
            error_classification=request.error_classification,
            metadata=request.metadata,
            recorded_at=request.recorded_at,
        )
        self.events.append(record)
        return record


class _FakeTelemetryAdapter(TelemetryAdapter):
    def __init__(self) -> None:
        self.emitted = 0

    def emit_span(self, event) -> None:
        _ = event
        self.emitted += 1


class Phase5TelemetryTestCase(unittest.TestCase):
    def test_record_event_maps_usage_and_emits_span(self) -> None:
        pricing = ModelPricingRecord(
            id=9,
            provider="openai",
            model_name="gpt-4o-mini",
            currency="USD",
            input_cost_per_1k_tokens=Decimal("0.1000"),
            output_cost_per_1k_tokens=Decimal("0.4000"),
            effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            effective_to=None,
        )
        telemetry_repository = _FakeTelemetryRepository()
        adapter = _FakeTelemetryAdapter()
        service = TelemetryService(
            telemetry_repository=telemetry_repository,
            cost_calculator=CostCalculatorService(_FakePricingRepository(pricing)),
            adapter=adapter,
        )

        record = service.record_event(
            request=TelemetryEventRequest(
                event_type="chat_request",
                run_id=None,
                request_id="req-1",
                correlation_id="chat-req-1",
                stage="synthesis",
                status="success",
                provider="openai",
                model_name="gpt-4o-mini",
                input_tokens=100,
                output_tokens=50,
                error_classification=None,
                metadata={"vector_kept": 3},
                recorded_at=datetime(2026, 4, 3, tzinfo=timezone.utc),
            ),
            span_name="chat.synthesis",
            span_kind="node",
            allow_missing_pricing=False,
        )
        self.assertEqual(record.pricing_version_id, 9)
        self.assertEqual(record.cost_amount, Decimal("0.030000"))
        self.assertEqual(len(telemetry_repository.events), 1)
        self.assertEqual(adapter.emitted, 1)

    def test_classify_failure_maps_known_errors(self) -> None:
        telemetry_repository = _FakeTelemetryRepository()
        adapter = _FakeTelemetryAdapter()
        service = TelemetryService(
            telemetry_repository=telemetry_repository,
            cost_calculator=CostCalculatorService(_FakePricingRepository(None)),
            adapter=adapter,
        )
        self.assertEqual(service.classify_failure(TimeoutError("slow")), "timeout")
        self.assertEqual(service.classify_failure(ValueError("bad")), "runtime")


if __name__ == "__main__":
    unittest.main()
