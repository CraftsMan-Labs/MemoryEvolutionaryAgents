from __future__ import annotations

from .adapters import FileSystemObsidianAdapter, HttpQdrantAdapter
from .extraction_service import WorkflowExtractionService
from .persistence import Phase2Repository, PostgresConnectionFactory
from .service import Phase2IngestionService
from .workflow_runner import SimpleAgentsWorkflowRunner
from ..phase3.service import OntologyEvolutionService
from ..phase5.service import TelemetryService
from ..phase6.service import FileProgressService
from ..run_tracking import RunTrackingService
from ..settings import AppSettings


def build_phase2_service(
    settings: AppSettings,
    run_tracking: RunTrackingService,
    phase3_ontology: OntologyEvolutionService | None,
    phase6_progress: FileProgressService | None,
    telemetry_service: TelemetryService | None,
) -> Phase2IngestionService | None:
    if settings.phase2_enabled is False:
        return None
    if settings.database_url is None:
        raise ValueError("MEA_DATABASE_URL is required when phase2 is enabled")

    connection_factory = PostgresConnectionFactory(settings.database_url)
    repository = Phase2Repository(connection_factory)
    extraction_service = WorkflowExtractionService()
    qdrant_adapter = HttpQdrantAdapter(
        base_url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        api_key=settings.qdrant_api_key,
    )
    obsidian_adapter = FileSystemObsidianAdapter(settings.obsidian_vault_path)
    runner = SimpleAgentsWorkflowRunner(
        workflow_path=settings.phase2_workflow_path,
        provider=settings.workflow_provider,
        model=settings.workflow_model,
        api_base=settings.workflow_api_base,
        api_key=settings.workflow_api_key,
        stage_timeout_seconds=settings.stage_timeout_seconds,
    )
    return Phase2IngestionService(
        run_tracking=run_tracking,
        repository=repository,
        workflow_runner=runner,
        extraction_service=extraction_service,
        qdrant_adapter=qdrant_adapter,
        obsidian_adapter=obsidian_adapter,
        ontology_service=phase3_ontology,
        phase6_progress=phase6_progress,
        telemetry_service=telemetry_service,
    )
