from __future__ import annotations

from ..phase2.persistence import PostgresConnectionFactory
from ..phase3.service import OntologyEvolutionService
from ..settings import AppSettings
from .adapters import HttpQdrantSearchAdapter
from .linkwalk import ObsidianLinkGraphReader
from .persistence import Phase4Repository
from .service import (
    ChatOrchestrationService,
    LinkWalkRetrievalService,
    VectorRetrievalService,
)
from .synthesis import ChatSynthesisService
from .validation import ChatQueryValidationService


def build_phase4_service(
    settings: AppSettings,
    ontology_service: OntologyEvolutionService | None,
) -> ChatOrchestrationService | None:
    if settings.phase4_enabled is False:
        return None
    if settings.database_url is None:
        raise ValueError("MEA_DATABASE_URL is required when phase4 is enabled")

    connection_factory = PostgresConnectionFactory(settings.database_url)
    repository = Phase4Repository(connection_factory)
    qdrant_adapter = HttpQdrantSearchAdapter(
        base_url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        api_key=settings.qdrant_api_key,
    )
    validator = ChatQueryValidationService()
    vector_retrieval = VectorRetrievalService(
        qdrant_adapter=qdrant_adapter,
        repository=repository,
    )
    linkwalk_retrieval = LinkWalkRetrievalService(
        graph_reader=ObsidianLinkGraphReader(settings.obsidian_vault_path),
        repository=repository,
    )
    synthesis = ChatSynthesisService()
    return ChatOrchestrationService(
        validator=validator,
        vector_retrieval=vector_retrieval,
        linkwalk_retrieval=linkwalk_retrieval,
        synthesis=synthesis,
        ontology_service=ontology_service,
    )
