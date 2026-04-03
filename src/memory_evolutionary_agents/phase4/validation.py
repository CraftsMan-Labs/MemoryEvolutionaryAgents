from __future__ import annotations

from datetime import date

from .contracts import ChatQueryFilters, ChatQueryRequest
from .errors import Phase4ValidationError


class ChatQueryValidationService:
    def validate(self, request: ChatQueryRequest) -> ChatQueryRequest:
        if len(request.query.strip()) == 0:
            raise Phase4ValidationError("query must not be empty")

        cleaned_filters = ChatQueryFilters(
            project=_clean_optional_text(request.filters.project),
            tags=_clean_string_list(request.filters.tags),
            ontology_terms=_clean_string_list(request.filters.ontology_terms),
            taxonomy_tags=_clean_string_list(request.filters.taxonomy_tags),
            event_date_from=_clean_optional_text(request.filters.event_date_from),
            event_date_to=_clean_optional_text(request.filters.event_date_to),
        )

        self._validate_date_range(cleaned_filters)
        self._validate_filter_combination(cleaned_filters)

        return request.model_copy(
            update={
                "query": request.query.strip(),
                "filters": cleaned_filters,
            }
        )

    def _validate_date_range(self, filters: ChatQueryFilters) -> None:
        from_date = _parse_iso_date(filters.event_date_from, "event_date_from")
        to_date = _parse_iso_date(filters.event_date_to, "event_date_to")
        if from_date is not None and to_date is not None and from_date > to_date:
            raise Phase4ValidationError("event_date_from must be <= event_date_to")

    def _validate_filter_combination(self, filters: ChatQueryFilters) -> None:
        if (
            filters.project is None
            and len(filters.tags) == 0
            and len(filters.ontology_terms) == 0
            and len(filters.taxonomy_tags) == 0
            and filters.event_date_from is None
            and filters.event_date_to is None
        ):
            return
        has_semantic_scope = (
            filters.project is not None
            or len(filters.tags) > 0
            or len(filters.ontology_terms) > 0
            or len(filters.taxonomy_tags) > 0
        )
        if has_semantic_scope:
            return
        raise Phase4ValidationError(
            "date-only filters are not allowed; include project/tag/ontology scope"
        )


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if len(cleaned) == 0:
        return None
    return cleaned


def _clean_string_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = value.strip()
        if len(cleaned) == 0:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(cleaned)
    return ordered


def _parse_iso_date(value: str | None, field_name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise Phase4ValidationError(
            f"{field_name} must be ISO date YYYY-MM-DD"
        ) from exc
