from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from memory_evolutionary_agents.phase5.contracts import (
    ModelPricingRecord,
    TelemetryEventRequest,
)
from memory_evolutionary_agents.phase5.costing import CostCalculatorService
from memory_evolutionary_agents.phase5.errors import MissingPricingError


class _FakePricingRepository:
    def __init__(self, records: list[ModelPricingRecord]) -> None:
        self._records = records

    def find_effective_pricing(self, provider: str, model_name: str, at_time: datetime):
        for record in self._records:
            if record.provider != provider or record.model_name != model_name:
                continue
            if record.effective_from <= at_time and (
                record.effective_to is None or record.effective_to > at_time
            ):
                return record
        return None


class Phase5CostingTestCase(unittest.TestCase):
    def test_cost_calculates_across_pricing_versions(self) -> None:
        early = ModelPricingRecord(
            id=1,
            provider="openai",
            model_name="gpt-4o-mini",
            currency="USD",
            input_cost_per_1k_tokens=Decimal("0.1500"),
            output_cost_per_1k_tokens=Decimal("0.6000"),
            effective_from=datetime(2026, 4, 1, tzinfo=timezone.utc),
            effective_to=datetime(2026, 4, 2, tzinfo=timezone.utc),
        )
        late = early.model_copy(
            update={
                "id": 2,
                "input_cost_per_1k_tokens": Decimal("0.2000"),
                "effective_from": datetime(2026, 4, 2, tzinfo=timezone.utc),
                "effective_to": None,
            }
        )
        service = CostCalculatorService(_FakePricingRepository([early, late]))

        early_cost = service.compute_cost(
            request=TelemetryEventRequest(
                event_type="chat_request",
                run_id=None,
                request_id="req-1",
                correlation_id="chat-1",
                stage="synthesis",
                status="success",
                provider="openai",
                model_name="gpt-4o-mini",
                input_tokens=1000,
                output_tokens=500,
                error_classification=None,
                metadata={},
                recorded_at=datetime(2026, 4, 1, 12, tzinfo=timezone.utc),
            ),
            allow_missing_pricing=False,
        )
        self.assertEqual(early_cost.pricing.id, 1)
        self.assertEqual(early_cost.cost_amount, Decimal("0.450000"))

        late_cost = service.compute_cost(
            request=TelemetryEventRequest(
                event_type="chat_request",
                run_id=None,
                request_id="req-2",
                correlation_id="chat-2",
                stage="synthesis",
                status="success",
                provider="openai",
                model_name="gpt-4o-mini",
                input_tokens=1000,
                output_tokens=500,
                error_classification=None,
                metadata={},
                recorded_at=datetime(2026, 4, 3, 12, tzinfo=timezone.utc),
            ),
            allow_missing_pricing=False,
        )
        self.assertEqual(late_cost.pricing.id, 2)
        self.assertEqual(late_cost.cost_amount, Decimal("0.500000"))

    def test_missing_pricing_raises_actionable_error(self) -> None:
        service = CostCalculatorService(_FakePricingRepository([]))
        with self.assertRaises(MissingPricingError) as context:
            service.compute_cost(
                request=TelemetryEventRequest(
                    event_type="chat_request",
                    run_id=None,
                    request_id="req-3",
                    correlation_id="chat-3",
                    stage="synthesis",
                    status="success",
                    provider="openai",
                    model_name="gpt-4o-mini",
                    input_tokens=10,
                    output_tokens=20,
                    error_classification=None,
                    metadata={},
                    recorded_at=datetime.now(tz=timezone.utc),
                ),
                allow_missing_pricing=False,
            )
        self.assertIn("provider=openai", str(context.exception))


if __name__ == "__main__":
    unittest.main()
