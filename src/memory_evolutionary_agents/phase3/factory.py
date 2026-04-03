from __future__ import annotations

from ..phase2.persistence import PostgresConnectionFactory
from ..settings import AppSettings
from .matcher import OntologyMatcherService
from .persistence import Phase3Repository
from .service import OntologyEvolutionService


def build_phase3_service(settings: AppSettings) -> OntologyEvolutionService | None:
    if settings.phase3_enabled is False:
        return None
    if settings.database_url is None:
        raise ValueError("MEA_DATABASE_URL is required when phase3 is enabled")

    connection_factory = PostgresConnectionFactory(settings.database_url)
    repository = Phase3Repository(connection_factory)
    matcher = OntologyMatcherService(threshold=settings.phase3_match_threshold)
    return OntologyEvolutionService(repository=repository, matcher=matcher)
