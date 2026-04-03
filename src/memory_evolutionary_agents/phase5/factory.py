from __future__ import annotations

from dataclasses import dataclass

from ..run_tracking import RunTrackingService
from ..source_registry import SourceRegistryService
from ..phase2.persistence import PostgresConnectionFactory
from ..settings import AppSettings
from .adapters import LangfuseTelemetryAdapter, NoopTelemetryAdapter, TelemetryAdapter
from .costing import CostCalculatorService
from .persistence import PricingRepository, TelemetryRepository
from .service import Phase5StatusService, TelemetryService


@dataclass(frozen=True)
class Phase5Services:
    telemetry: TelemetryService
    status: Phase5StatusService


def build_phase5_services(
    settings: AppSettings,
    run_tracking: RunTrackingService,
    source_registry: SourceRegistryService,
) -> Phase5Services | None:
    if settings.phase5_enabled is False:
        return None
    if settings.database_url is None:
        raise ValueError("MEA_DATABASE_URL is required when phase5 is enabled")

    connection_factory = PostgresConnectionFactory(settings.database_url)
    telemetry_repository = TelemetryRepository(connection_factory)
    pricing_repository = PricingRepository(connection_factory)
    cost_calculator = CostCalculatorService(pricing_repository)
    adapter = _build_telemetry_adapter(settings)
    telemetry_service = TelemetryService(
        telemetry_repository=telemetry_repository,
        cost_calculator=cost_calculator,
        adapter=adapter,
    )
    status_service = Phase5StatusService(
        run_tracking=run_tracking,
        source_registry=source_registry,
        telemetry_repository=telemetry_repository,
    )
    return Phase5Services(telemetry=telemetry_service, status=status_service)


def _build_telemetry_adapter(settings: AppSettings) -> TelemetryAdapter:
    if settings.langfuse_enabled is False:
        return NoopTelemetryAdapter()
    if settings.langfuse_base_url is None:
        raise ValueError("MEA_LANGFUSE_BASE_URL is required when Langfuse is enabled")
    if settings.langfuse_public_key is None:
        raise ValueError("MEA_LANGFUSE_PUBLIC_KEY is required when Langfuse is enabled")
    if settings.langfuse_secret_key is None:
        raise ValueError("MEA_LANGFUSE_SECRET_KEY is required when Langfuse is enabled")
    return LangfuseTelemetryAdapter(
        base_url=settings.langfuse_base_url,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
    )
