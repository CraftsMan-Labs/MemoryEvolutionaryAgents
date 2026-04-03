from __future__ import annotations

from dataclasses import dataclass

from .database import Database
from .onboarding import OnboardingService
from .phase2.factory import build_phase2_service
from .phase2.service import Phase2IngestionService
from .phase3.factory import build_phase3_service
from .phase3.service import OntologyEvolutionService
from .phase4.factory import build_phase4_service
from .phase4.service import ChatOrchestrationService
from .phase5.factory import build_phase5_services
from .phase5.service import Phase5StatusService, TelemetryService
from .phase6.factory import build_phase6_service
from .phase6.service import FileProgressService
from .run_tracking import RunTrackingService
from .scanner import IncrementalScanner
from .scheduler import CronIngestionScheduler
from .security import SecretCipher
from .settings import AppSettings, load_settings
from .source_registry import SourceRegistryService


@dataclass(frozen=True)
class AppContainer:
    settings: AppSettings
    database: Database
    source_registry: SourceRegistryService
    run_tracking: RunTrackingService
    onboarding: OnboardingService
    scanner: IncrementalScanner
    scheduler: CronIngestionScheduler
    phase2_ingestion: Phase2IngestionService | None
    phase3_ontology: OntologyEvolutionService | None
    phase4_chat: ChatOrchestrationService | None
    phase5_telemetry: TelemetryService | None
    phase5_status: Phase5StatusService | None
    phase6_progress: FileProgressService


def build_container() -> AppContainer:
    settings = load_settings()
    database = Database(settings.db_path)
    database.initialize()
    source_registry = SourceRegistryService(database)
    run_tracking = RunTrackingService(database)
    cipher = SecretCipher.from_env()
    onboarding = OnboardingService(
        database=database,
        cipher=cipher,
        local_qdrant_url=settings.qdrant_url,
    )
    scanner = IncrementalScanner()
    scheduler = CronIngestionScheduler(
        source_registry=source_registry,
        run_tracking=run_tracking,
        scanner=scanner,
        interval_seconds=settings.scan_interval_seconds,
        cycle_timeout_seconds=settings.scan_cycle_timeout_seconds,
    )
    phase3_ontology = build_phase3_service(settings=settings)
    phase5_services = build_phase5_services(
        settings=settings,
        run_tracking=run_tracking,
        source_registry=source_registry,
    )
    phase6_progress = build_phase6_service(database=database, run_tracking=run_tracking)
    phase4_chat = build_phase4_service(
        settings=settings,
        ontology_service=phase3_ontology,
        telemetry_service=None
        if phase5_services is None
        else phase5_services.telemetry,
    )
    phase2_ingestion = build_phase2_service(
        settings=settings,
        run_tracking=run_tracking,
        phase3_ontology=phase3_ontology,
        phase6_progress=phase6_progress,
        telemetry_service=None
        if phase5_services is None
        else phase5_services.telemetry,
    )
    return AppContainer(
        settings=settings,
        database=database,
        source_registry=source_registry,
        run_tracking=run_tracking,
        onboarding=onboarding,
        scanner=scanner,
        scheduler=scheduler,
        phase2_ingestion=phase2_ingestion,
        phase3_ontology=phase3_ontology,
        phase4_chat=phase4_chat,
        phase5_telemetry=None if phase5_services is None else phase5_services.telemetry,
        phase5_status=None if phase5_services is None else phase5_services.status,
        phase6_progress=phase6_progress,
    )
