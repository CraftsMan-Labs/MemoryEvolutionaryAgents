from __future__ import annotations

import unittest

from memory_evolutionary_agents.phase3.contracts import FilterAliasResolutionResponse
from memory_evolutionary_agents.phase4.contracts import (
    CanonicalMemoryRecord,
    ChatQueryFilters,
    ChatQueryRequest,
    LinkWalkCandidate,
    LinkWalkResponse,
    MemoryChunkRecord,
    QdrantScoredPoint,
    QdrantSearchResponse,
)
from memory_evolutionary_agents.phase4.service import (
    ChatOrchestrationService,
    LinkWalkRetrievalService,
    VectorRetrievalService,
)
from memory_evolutionary_agents.phase4.synthesis import ChatSynthesisService
from memory_evolutionary_agents.phase4.validation import ChatQueryValidationService


class _FakeQdrantAdapter:
    def search(self, request):
        _ = request
        return QdrantSearchResponse(
            points=[
                QdrantScoredPoint(
                    point_id="chunk-1",
                    score=0.82,
                    payload={
                        "file_path": "/tmp/source/a.md",
                        "chunk_id": "chunk-1",
                        "text": "Telemetry issue fixed by Postgres index tuning",
                        "project": "Telemetry",
                        "tags": ["database"],
                        "ontology_terms": ["Postgres"],
                        "taxonomy_tags": ["database"],
                        "event_date": "2026-04-03",
                        "obsidian_note_path": "/tmp/vault/A.md",
                    },
                )
            ]
        )


class _FakeRepository:
    def list_memories_for_filters(self, filters, limit):
        _ = (filters, limit)
        return [
            CanonicalMemoryRecord(
                id=1,
                source_path="/tmp/source",
                file_path="/tmp/source/a.md",
                project="Telemetry",
                event_date="2026-04-03",
                tags=["database"],
                ontology_terms=["Postgres"],
                taxonomy_tags=["database"],
                obsidian_note_path="/tmp/vault/A.md",
            ),
            CanonicalMemoryRecord(
                id=2,
                source_path="/tmp/source",
                file_path="/tmp/source/b.md",
                project="Telemetry",
                event_date="2026-04-04",
                tags=["database"],
                ontology_terms=["Index"],
                taxonomy_tags=["database"],
                obsidian_note_path="/tmp/vault/B.md",
            ),
        ]

    def list_memories_by_note_paths(self, note_paths):
        if "/tmp/vault/B.md" in note_paths:
            return [
                CanonicalMemoryRecord(
                    id=2,
                    source_path="/tmp/source",
                    file_path="/tmp/source/b.md",
                    project="Telemetry",
                    event_date="2026-04-04",
                    tags=["database"],
                    ontology_terms=["Index"],
                    taxonomy_tags=["database"],
                    obsidian_note_path="/tmp/vault/B.md",
                )
            ]
        return []

    def list_chunks_for_memory_ids(self, memory_ids):
        if 2 in memory_ids:
            return [
                MemoryChunkRecord(
                    memory_id=2,
                    chunk_id="chunk-2",
                    chunk_index=0,
                    chunk_text="Index tuning removed telemetry query timeout",
                )
            ]
        return []


class _FakeGraphReader:
    def walk(self, request):
        _ = request
        return LinkWalkResponse(
            candidates=[
                LinkWalkCandidate(note_path="/tmp/vault/A.md", depth=0),
                LinkWalkCandidate(note_path="/tmp/vault/B.md", depth=1),
            ]
        )


class _FakeOntologyService:
    def resolve_filter_aliases(self, request):
        return FilterAliasResolutionResponse(
            ontology_terms=["Postgres"],
            taxonomy_tags=request.taxonomy_tags,
            ontology_aliases={"Postgress": "Postgres"},
            taxonomy_aliases={},
        )


class Phase4ServiceTestCase(unittest.TestCase):
    def test_dual_retrieval_and_synthesis_returns_citations(self) -> None:
        repository = _FakeRepository()
        vector = VectorRetrievalService(_FakeQdrantAdapter(), repository)
        linkwalk = LinkWalkRetrievalService(_FakeGraphReader(), repository)
        service = ChatOrchestrationService(
            validator=ChatQueryValidationService(),
            vector_retrieval=vector,
            linkwalk_retrieval=linkwalk,
            synthesis=ChatSynthesisService(),
            ontology_service=_FakeOntologyService(),
        )
        response = service.query(
            ChatQueryRequest(
                query="Postgress timeout",
                top_k=3,
                filters=ChatQueryFilters(
                    project="Telemetry",
                    tags=["database"],
                    ontology_terms=["Postgress"],
                ),
            )
        )

        self.assertGreaterEqual(response.confidence, 0.0)
        self.assertGreaterEqual(len(response.citations), 1)
        self.assertEqual(
            response.retrieval_diagnostics.resolved_ontology_aliases.get("Postgress"),
            "Postgres",
        )

    def test_golden_citation_format_stays_stable(self) -> None:
        synthesis = ChatSynthesisService()
        answer, confidence, citations = synthesis.synthesize_answer(
            query="q",
            vector_results=[],
            linkwalk_results=[],
            top_k=2,
        )
        self.assertEqual(
            {
                "answer": answer,
                "confidence": confidence,
                "citations": [item.model_dump() for item in citations],
            },
            {
                "answer": (
                    "I could not find matching memories for this query under the current "
                    "filters. Try relaxing filters or adding more context."
                ),
                "confidence": 0.0,
                "citations": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
