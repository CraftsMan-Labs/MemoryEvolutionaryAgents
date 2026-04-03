from __future__ import annotations

from typing import Callable, Sequence

from .contracts import (
    FilterAliasResolutionRequest,
    FilterAliasResolutionResponse,
    OntologyEvolutionRequest,
    OntologyEvolutionResult,
    ProposalDetailResponse,
    ProposalStatus,
    ProposalType,
    RegistryStatus,
    RelationEdge,
    RegistryTermRecord,
    SchemaProposalRecord,
)
from .errors import InvalidProposalTransitionError
from .matcher import OntologyMatcherService
from .persistence import Phase3Repository, SchemaProposalCreateRequest


class OntologyEvolutionService:
    def __init__(
        self,
        repository: Phase3Repository,
        matcher: OntologyMatcherService,
    ) -> None:
        self._repository = repository
        self._matcher = matcher

    def evolve(self, request: OntologyEvolutionRequest) -> OntologyEvolutionResult:
        ontology_registry = self._repository.list_ontology_terms()
        taxonomy_registry = self._repository.list_taxonomy_tags()

        ontology_terms: list[str] = []
        taxonomy_tags: list[str] = []
        proposal_ids: list[int] = []

        ontology_by_name: dict[str, int] = {}
        for candidate in _unique_values([request.project, *request.entities]):
            match = self._matcher.match(candidate, ontology_registry)
            if match.matched is not None:
                ontology_terms.append(match.matched.name)
                ontology_by_name[match.matched.name] = match.matched.id
                continue
            provisional = self._repository.upsert_ontology_term(
                name=candidate,
                status=RegistryStatus.PROVISIONAL,
            )
            ontology_terms.append(provisional.name)
            ontology_by_name[provisional.name] = provisional.id
            proposal = self._repository.create_or_update_proposal(
                SchemaProposalCreateRequest(
                    proposal_type=ProposalType.ONTOLOGY_TERM,
                    candidate_value=candidate,
                    normalized_value=provisional.normalized_name,
                    confidence=match.confidence,
                    context={
                        "source_id": request.source_id,
                        "source_path": request.source_path,
                        "file_path": request.file_path,
                    },
                    idempotency_key=_proposal_key(
                        ProposalType.ONTOLOGY_TERM,
                        request.content_hash,
                        provisional.normalized_name,
                    ),
                    linked_record_id=provisional.id,
                )
            )
            proposal_ids.append(proposal.id)

        for candidate in _unique_values(request.tags):
            match = self._matcher.match(candidate, taxonomy_registry)
            if match.matched is not None:
                taxonomy_tags.append(match.matched.name)
                continue
            provisional = self._repository.upsert_taxonomy_tag(
                name=candidate,
                status=RegistryStatus.PROVISIONAL,
            )
            taxonomy_tags.append(provisional.name)
            proposal = self._repository.create_or_update_proposal(
                SchemaProposalCreateRequest(
                    proposal_type=ProposalType.TAXONOMY_TAG,
                    candidate_value=candidate,
                    normalized_value=provisional.normalized_name,
                    confidence=match.confidence,
                    context={
                        "source_id": request.source_id,
                        "source_path": request.source_path,
                        "file_path": request.file_path,
                    },
                    idempotency_key=_proposal_key(
                        ProposalType.TAXONOMY_TAG,
                        request.content_hash,
                        provisional.normalized_name,
                    ),
                    linked_record_id=provisional.id,
                )
            )
            proposal_ids.append(proposal.id)

        relation_edges = self._build_relation_edges(request, ontology_by_name)

        return OntologyEvolutionResult(
            ontology_terms=_unique_values(ontology_terms),
            taxonomy_tags=_unique_values(taxonomy_tags),
            relation_edges=relation_edges,
            proposal_ids=_unique_ints(proposal_ids),
        )

    def list_proposals(
        self,
        status: ProposalStatus | None,
        proposal_type: ProposalType | None,
        limit: int,
    ) -> list[SchemaProposalRecord]:
        return self._repository.list_proposals(status, proposal_type, limit)

    def get_proposal_detail(self, proposal_id: int) -> ProposalDetailResponse:
        proposal = self._repository.get_proposal(proposal_id)
        events = self._repository.list_proposal_events(proposal_id)
        return ProposalDetailResponse(proposal=proposal, events=events)

    def approve_proposal(
        self, proposal_id: int, actor: str, note: str | None
    ) -> SchemaProposalRecord:
        proposal = self._repository.get_proposal(proposal_id)
        self._assert_transition_allowed(proposal.status)
        if proposal.linked_record_id is not None:
            if proposal.proposal_type == ProposalType.ONTOLOGY_TERM:
                self._repository.update_ontology_term_status(
                    proposal.linked_record_id,
                    status=RegistryStatus.APPROVED,
                    merged_into_term_id=None,
                )
            if proposal.proposal_type == ProposalType.TAXONOMY_TAG:
                self._repository.update_taxonomy_tag_status(
                    proposal.linked_record_id,
                    status=RegistryStatus.APPROVED,
                    merged_into_tag_id=None,
                )
        return self._repository.update_proposal_status(
            proposal_id,
            to_status=ProposalStatus.APPROVED,
            changed_by=actor,
            note=note,
            merged_into_record_id=None,
        )

    def reject_proposal(
        self, proposal_id: int, actor: str, note: str | None
    ) -> SchemaProposalRecord:
        proposal = self._repository.get_proposal(proposal_id)
        self._assert_transition_allowed(proposal.status)
        if proposal.linked_record_id is not None:
            if proposal.proposal_type == ProposalType.ONTOLOGY_TERM:
                self._repository.update_ontology_term_status(
                    proposal.linked_record_id,
                    status=RegistryStatus.REJECTED,
                    merged_into_term_id=None,
                )
            if proposal.proposal_type == ProposalType.TAXONOMY_TAG:
                self._repository.update_taxonomy_tag_status(
                    proposal.linked_record_id,
                    status=RegistryStatus.REJECTED,
                    merged_into_tag_id=None,
                )
        return self._repository.update_proposal_status(
            proposal_id,
            to_status=ProposalStatus.REJECTED,
            changed_by=actor,
            note=note,
            merged_into_record_id=None,
        )

    def merge_proposal(
        self,
        proposal_id: int,
        target_record_id: int,
        actor: str,
        note: str | None,
    ) -> SchemaProposalRecord:
        proposal = self._repository.get_proposal(proposal_id)
        self._assert_transition_allowed(proposal.status)
        if proposal.linked_record_id is not None:
            if proposal.proposal_type == ProposalType.ONTOLOGY_TERM:
                self._repository.update_ontology_term_status(
                    proposal.linked_record_id,
                    status=RegistryStatus.MERGED,
                    merged_into_term_id=target_record_id,
                )
            if proposal.proposal_type == ProposalType.TAXONOMY_TAG:
                self._repository.update_taxonomy_tag_status(
                    proposal.linked_record_id,
                    status=RegistryStatus.MERGED,
                    merged_into_tag_id=target_record_id,
                )
        return self._repository.update_proposal_status(
            proposal_id,
            to_status=ProposalStatus.MERGED,
            changed_by=actor,
            note=note,
            merged_into_record_id=target_record_id,
        )

    def resolve_filter_aliases(
        self, request: FilterAliasResolutionRequest
    ) -> FilterAliasResolutionResponse:
        resolved_ontology_terms: list[str] = []
        resolved_taxonomy_tags: list[str] = []
        ontology_aliases: dict[str, str] = {}
        taxonomy_aliases: dict[str, str] = {}

        for raw_value in _unique_values(request.ontology_terms):
            resolved = self._resolve_ontology_value(raw_value)
            resolved_ontology_terms.append(resolved.name)
            ontology_aliases[raw_value] = resolved.name

        for raw_value in _unique_values(request.taxonomy_tags):
            resolved = self._resolve_taxonomy_value(raw_value)
            resolved_taxonomy_tags.append(resolved.name)
            taxonomy_aliases[raw_value] = resolved.name

        return FilterAliasResolutionResponse(
            ontology_terms=_unique_values(resolved_ontology_terms),
            taxonomy_tags=_unique_values(resolved_taxonomy_tags),
            ontology_aliases=ontology_aliases,
            taxonomy_aliases=taxonomy_aliases,
        )

    def _build_relation_edges(
        self,
        request: OntologyEvolutionRequest,
        ontology_by_name: dict[str, int],
    ) -> list[RelationEdge]:
        if request.project is None:
            return []
        project_name = request.project
        source_term_id = ontology_by_name.get(project_name)
        if source_term_id is None:
            return []

        edges: list[RelationEdge] = []
        for entity in _unique_values(request.entities):
            if entity == project_name:
                continue
            target_term_id = ontology_by_name.get(entity)
            if target_term_id is None:
                continue
            relation = self._repository.upsert_relation(
                source_term_id=source_term_id,
                predicate="mentions",
                target_term_id=target_term_id,
                status=RegistryStatus.PROVISIONAL,
            )
            edges.append(
                RelationEdge(
                    source=project_name,
                    predicate=relation.predicate,
                    target=entity,
                    status=relation.status,
                )
            )
        return edges

    def _assert_transition_allowed(self, status: ProposalStatus) -> None:
        if status != ProposalStatus.PROVISIONAL:
            raise InvalidProposalTransitionError(
                "only provisional proposals can be transitioned"
            )

    def _resolve_ontology_value(self, value: str) -> RegistryTermRecord:
        normalized_value = _normalize_value(value)
        record = self._repository.find_ontology_term_by_normalized(normalized_value)
        if record is None:
            return RegistryTermRecord(
                id=0,
                name=value,
                normalized_name=normalized_value,
                status=RegistryStatus.PROVISIONAL,
                merged_into_id=None,
            )
        return self._resolve_merged_record(
            initial=record,
            by_id_lookup=self._repository.get_ontology_term_by_id,
        )

    def _resolve_taxonomy_value(self, value: str) -> RegistryTermRecord:
        normalized_value = _normalize_value(value)
        record = self._repository.find_taxonomy_tag_by_normalized(normalized_value)
        if record is None:
            return RegistryTermRecord(
                id=0,
                name=value,
                normalized_name=normalized_value,
                status=RegistryStatus.PROVISIONAL,
                merged_into_id=None,
            )
        return self._resolve_merged_record(
            initial=record,
            by_id_lookup=self._repository.get_taxonomy_tag_by_id,
        )

    def _resolve_merged_record(
        self,
        initial: RegistryTermRecord,
        by_id_lookup: Callable[[int], RegistryTermRecord | None],
    ) -> RegistryTermRecord:
        current = initial
        for _ in range(10):
            if current.merged_into_id is None:
                return current
            next_record = by_id_lookup(current.merged_into_id)
            if next_record is None:
                return current
            current = next_record
        return current


def _proposal_key(
    proposal_type: ProposalType,
    content_hash: str,
    normalized_value: str,
) -> str:
    return f"{proposal_type.value}:{content_hash}:{normalized_value}"


def _normalize_value(value: str) -> str:
    return " ".join(value.lower().split())


def _unique_values(values: Sequence[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) is False:
            continue
        compact = value.strip()
        if len(compact) == 0:
            continue
        if compact in seen:
            continue
        seen.add(compact)
        result.append(compact)
    return result


def _unique_ints(values: list[int]) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
