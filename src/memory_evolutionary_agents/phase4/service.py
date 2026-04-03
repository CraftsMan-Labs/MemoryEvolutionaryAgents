from __future__ import annotations

import hashlib
from pathlib import Path
import re

from ..phase3.contracts import FilterAliasResolutionRequest
from ..phase3.service import OntologyEvolutionService
from .adapters import QdrantSearchAdapter
from .contracts import (
    CanonicalMemoryRecord,
    ChatQueryRequest,
    ChatQueryResponse,
    LinkWalkRequest,
    QdrantSearchResponse,
    QdrantSearchRequest,
    RetrievalDiagnostics,
    RetrievalResultRecord,
)
from .linkwalk import ObsidianLinkGraphReader
from .persistence import Phase4Repository
from .synthesis import ChatSynthesisService
from .validation import ChatQueryValidationService
from .errors import Phase4AdapterError


class VectorRetrievalService:
    def __init__(
        self,
        qdrant_adapter: QdrantSearchAdapter,
        repository: Phase4Repository,
    ) -> None:
        self._qdrant_adapter = qdrant_adapter
        self._repository = repository

    def retrieve(self, request: ChatQueryRequest) -> list[RetrievalResultRecord]:
        response = self._search_with_adaptive_dimension(request)
        memories = self._repository.list_memories_for_filters(
            filters=request.filters,
            limit=max(request.vector_top_k * 3, 30),
        )
        memory_by_file = {memory.file_path: memory for memory in memories}
        memory_by_note = {
            str(Path(memory.obsidian_note_path).resolve()): memory
            for memory in memories
            if memory.obsidian_note_path is not None
        }

        provisional: list[RetrievalResultRecord] = []
        for point in response.points:
            payload = point.payload
            file_path = _optional_string(payload.get("file_path"))
            note_path = _optional_string(payload.get("obsidian_note_path"))
            memory = None
            if file_path is not None:
                memory = memory_by_file.get(file_path)
            if memory is None and note_path is not None:
                resolved_note = str(Path(note_path).resolve())
                memory = memory_by_note.get(resolved_note)
            if memory is None:
                continue
            if _payload_matches_filters(payload, request):
                snippet = _build_snippet(payload, memory)
                provisional.append(
                    RetrievalResultRecord(
                        memory_id=memory.id,
                        source_path=memory.source_path,
                        file_path=memory.file_path,
                        note_path=memory.obsidian_note_path,
                        chunk_id=_optional_string(payload.get("chunk_id")),
                        snippet=snippet,
                        score=point.score,
                        normalized_score=0.0,
                        retrieval_path="vector_metadata",
                    )
                )
        return _normalize_and_rank(provisional)

    def _search_with_adaptive_dimension(
        self,
        request: ChatQueryRequest,
    ) -> QdrantSearchResponse:
        dimensions = 32
        for _ in range(2):
            vector = _embed_query(request.query, dimensions=dimensions)
            try:
                return self._qdrant_adapter.search(
                    QdrantSearchRequest(
                        vector=vector,
                        limit=request.vector_top_k,
                        project=request.filters.project,
                        tags=request.filters.tags,
                        ontology_terms=request.filters.ontology_terms,
                        taxonomy_tags=request.filters.taxonomy_tags,
                    )
                )
            except Phase4AdapterError as exc:
                expected_dim = _extract_expected_dim(str(exc))
                if expected_dim is None or expected_dim == dimensions:
                    raise
                dimensions = expected_dim
        raise RuntimeError("adaptive vector search retry failed")


class LinkWalkRetrievalService:
    def __init__(
        self,
        graph_reader: ObsidianLinkGraphReader,
        repository: Phase4Repository,
    ) -> None:
        self._graph_reader = graph_reader
        self._repository = repository

    def retrieve(
        self,
        request: ChatQueryRequest,
        vector_results: list[RetrievalResultRecord],
    ) -> list[RetrievalResultRecord]:
        seed_paths: list[str] = []
        for result in vector_results:
            if result.note_path is None:
                continue
            if result.note_path in seed_paths:
                continue
            seed_paths.append(result.note_path)

        if len(seed_paths) == 0:
            filter_seeds = self._repository.list_memories_for_filters(
                filters=request.filters,
                limit=max(request.top_k, 4),
            )
            for memory in filter_seeds:
                if memory.obsidian_note_path is None:
                    continue
                if memory.obsidian_note_path in seed_paths:
                    continue
                seed_paths.append(memory.obsidian_note_path)

        if len(seed_paths) == 0:
            return []

        walk = self._graph_reader.walk(
            request=LinkWalkRequest(
                seed_note_paths=seed_paths,
                max_depth=request.link_depth,
                max_fanout=request.link_fanout,
            )
        )
        walk_paths = [candidate.note_path for candidate in walk.candidates]
        memories = self._repository.list_memories_by_note_paths(walk_paths)
        filtered = [
            memory for memory in memories if _memory_matches_filters(memory, request)
        ]
        chunks = self._repository.list_chunks_for_memory_ids(
            [memory.id for memory in filtered]
        )
        chunk_by_memory: dict[int, list[str]] = {}
        for chunk in chunks:
            chunk_by_memory.setdefault(chunk.memory_id, []).append(chunk.chunk_text)

        depth_map = {
            candidate.note_path: candidate.depth for candidate in walk.candidates
        }
        provisional: list[RetrievalResultRecord] = []
        for memory in filtered:
            note_path = memory.obsidian_note_path
            depth = 0
            if note_path is not None:
                depth = depth_map.get(str(Path(note_path).resolve()), 0)
            snippet = _chunk_snippet(
                chunk_by_memory.get(memory.id, []), memory.file_path
            )
            lexical = _lexical_overlap_score(request.query, snippet)
            score = (1.0 / (1.0 + float(depth))) + lexical
            provisional.append(
                RetrievalResultRecord(
                    memory_id=memory.id,
                    source_path=memory.source_path,
                    file_path=memory.file_path,
                    note_path=memory.obsidian_note_path,
                    chunk_id=None,
                    snippet=snippet,
                    score=score,
                    normalized_score=0.0,
                    retrieval_path="obsidian_linkwalk",
                )
            )
        return _normalize_and_rank(provisional)


class ChatOrchestrationService:
    def __init__(
        self,
        validator: ChatQueryValidationService,
        vector_retrieval: VectorRetrievalService,
        linkwalk_retrieval: LinkWalkRetrievalService,
        synthesis: ChatSynthesisService,
        ontology_service: OntologyEvolutionService | None,
    ) -> None:
        self._validator = validator
        self._vector_retrieval = vector_retrieval
        self._linkwalk_retrieval = linkwalk_retrieval
        self._synthesis = synthesis
        self._ontology_service = ontology_service

    def query(self, request: ChatQueryRequest) -> ChatQueryResponse:
        validated = self._validator.validate(request)
        resolved_request, ontology_aliases, taxonomy_aliases = self._resolve_aliases(
            validated
        )

        vector_results = self._vector_retrieval.retrieve(resolved_request)
        linkwalk_results = self._linkwalk_retrieval.retrieve(
            resolved_request, vector_results
        )
        answer, confidence, citations = self._synthesis.synthesize_answer(
            query=resolved_request.query,
            vector_results=vector_results,
            linkwalk_results=linkwalk_results,
            top_k=resolved_request.top_k,
        )
        return ChatQueryResponse(
            answer=answer,
            confidence=confidence,
            citations=citations,
            retrieval_diagnostics=RetrievalDiagnostics(
                vector_candidates=resolved_request.vector_top_k,
                vector_kept=len(vector_results),
                linkwalk_candidates=(
                    len(linkwalk_results)
                    + len(
                        [
                            result
                            for result in vector_results
                            if result.note_path is not None
                        ]
                    )
                ),
                linkwalk_kept=len(linkwalk_results),
                resolved_ontology_aliases=ontology_aliases,
                resolved_taxonomy_aliases=taxonomy_aliases,
            ),
        )

    def _resolve_aliases(
        self,
        request: ChatQueryRequest,
    ) -> tuple[ChatQueryRequest, dict[str, str], dict[str, str]]:
        if self._ontology_service is None:
            return request, {}, {}
        resolution = self._ontology_service.resolve_filter_aliases(
            FilterAliasResolutionRequest(
                ontology_terms=request.filters.ontology_terms,
                taxonomy_tags=request.filters.taxonomy_tags,
            )
        )
        resolved = request.model_copy(
            update={
                "filters": request.filters.model_copy(
                    update={
                        "ontology_terms": resolution.ontology_terms,
                        "taxonomy_tags": resolution.taxonomy_tags,
                    }
                )
            }
        )
        return resolved, resolution.ontology_aliases, resolution.taxonomy_aliases


def _embed_query(query: str, dimensions: int) -> list[float]:
    if dimensions <= 0:
        return []
    encoded = query.encode("utf-8")
    data = b""
    index = 0
    while len(data) < dimensions:
        data += hashlib.sha256(encoded + bytes([index])).digest()
        index += 1
    return [float(value) / 255.0 for value in data[:dimensions]]


def _extract_expected_dim(error_message: str) -> int | None:
    match = re.search(r"expected dim:\s*(\d+)", error_message)
    if match is None:
        return None
    return int(match.group(1))


def _optional_string(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _payload_matches_filters(
    payload: dict[str, object], request: ChatQueryRequest
) -> bool:
    project = request.filters.project
    if project is not None and payload.get("project") != project:
        return False
    if (
        _contains_all(_list_from_payload(payload.get("tags")), request.filters.tags)
        is False
    ):
        return False
    if (
        _contains_all(
            _list_from_payload(payload.get("ontology_terms")),
            request.filters.ontology_terms,
        )
        is False
    ):
        return False
    if (
        _contains_all(
            _list_from_payload(payload.get("taxonomy_tags")),
            request.filters.taxonomy_tags,
        )
        is False
    ):
        return False
    return _date_matches(
        _optional_string(payload.get("event_date")),
        request.filters.event_date_from,
        request.filters.event_date_to,
    )


def _memory_matches_filters(
    memory: CanonicalMemoryRecord, request: ChatQueryRequest
) -> bool:
    if (
        request.filters.project is not None
        and memory.project != request.filters.project
    ):
        return False
    if _contains_all(memory.tags, request.filters.tags) is False:
        return False
    if _contains_all(memory.ontology_terms, request.filters.ontology_terms) is False:
        return False
    if _contains_all(memory.taxonomy_tags, request.filters.taxonomy_tags) is False:
        return False
    return _date_matches(
        memory.event_date,
        request.filters.event_date_from,
        request.filters.event_date_to,
    )


def _date_matches(
    value: str | None, from_date: str | None, to_date: str | None
) -> bool:
    if from_date is None and to_date is None:
        return True
    if value is None:
        return False
    if from_date is not None and value < from_date:
        return False
    if to_date is not None and value > to_date:
        return False
    return True


def _list_from_payload(value: object) -> list[str]:
    if isinstance(value, list) is False:
        return []
    values: list[str] = []
    for item in value:
        if isinstance(item, str):
            values.append(item)
    return values


def _contains_all(haystack: list[str], needles: list[str]) -> bool:
    if len(needles) == 0:
        return True
    lowered_haystack = {item.lower() for item in haystack}
    for needle in needles:
        if needle.lower() not in lowered_haystack:
            return False
    return True


def _build_snippet(payload: dict[str, object], memory: CanonicalMemoryRecord) -> str:
    text = _optional_string(payload.get("text"))
    if text is not None and len(text.strip()) > 0:
        return text.strip()
    return f"Memory from {memory.file_path}"


def _chunk_snippet(chunks: list[str], fallback_file_path: str) -> str:
    if len(chunks) == 0:
        return f"Memory from {fallback_file_path}"
    combined = " ".join(chunk.strip() for chunk in chunks if len(chunk.strip()) > 0)
    if len(combined) == 0:
        return f"Memory from {fallback_file_path}"
    return combined


def _normalize_and_rank(
    results: list[RetrievalResultRecord],
) -> list[RetrievalResultRecord]:
    if len(results) == 0:
        return []
    max_score = max(result.score for result in results)
    min_score = min(result.score for result in results)
    normalized: list[RetrievalResultRecord] = []
    for result in results:
        if max_score == min_score:
            score = 1.0
        else:
            score = (result.score - min_score) / (max_score - min_score)
        normalized.append(result.model_copy(update={"normalized_score": score}))

    by_memory: dict[int, RetrievalResultRecord] = {}
    for result in normalized:
        existing = by_memory.get(result.memory_id)
        if existing is None or result.normalized_score > existing.normalized_score:
            by_memory[result.memory_id] = result
    ranked = list(by_memory.values())
    ranked.sort(
        key=lambda item: (item.normalized_score, item.score, -item.memory_id),
        reverse=True,
    )
    return ranked


def _lexical_overlap_score(query: str, text: str) -> float:
    query_tokens = {token.lower() for token in query.split() if len(token) > 2}
    if len(query_tokens) == 0:
        return 0.0
    text_tokens = {token.lower() for token in text.split()}
    shared = query_tokens.intersection(text_tokens)
    return float(len(shared)) / float(len(query_tokens))
