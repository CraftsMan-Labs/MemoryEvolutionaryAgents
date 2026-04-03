from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .contracts import ModelPricingRecord, TelemetryEventRequest
from .errors import MissingPricingError
from .persistence import PricingRepository


class CostComputationResult:
    def __init__(
        self,
        pricing: ModelPricingRecord | None,
        cost_amount: Decimal | None,
        currency: str | None,
    ) -> None:
        self.pricing = pricing
        self.cost_amount = cost_amount
        self.currency = currency


class CostCalculatorService:
    def __init__(self, pricing_repository: PricingRepository) -> None:
        self._pricing_repository = pricing_repository

    def compute_cost(
        self,
        request: TelemetryEventRequest,
        allow_missing_pricing: bool,
    ) -> CostComputationResult:
        pricing = self._pricing_repository.find_effective_pricing(
            provider=request.provider,
            model_name=request.model_name,
            at_time=request.recorded_at,
        )
        if pricing is None:
            if allow_missing_pricing:
                return CostComputationResult(
                    pricing=None, cost_amount=None, currency=None
                )
            raise MissingPricingError(
                "missing pricing for provider/model at event time; "
                f"provider={request.provider}, model={request.model_name}, "
                f"recorded_at={request.recorded_at.isoformat()}"
            )

        input_cost = (
            Decimal(request.input_tokens) / Decimal(1000)
        ) * pricing.input_cost_per_1k_tokens
        output_cost = (
            Decimal(request.output_tokens) / Decimal(1000)
        ) * pricing.output_cost_per_1k_tokens
        total = (input_cost + output_cost).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        return CostComputationResult(
            pricing=pricing,
            cost_amount=total,
            currency=pricing.currency,
        )
