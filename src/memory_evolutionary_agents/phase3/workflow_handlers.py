from __future__ import annotations

from typing import Any


def collect_candidates(
    project: str | None,
    entities: list[str],
    tags: list[str],
    *,
    context: dict[str, Any],
) -> dict[str, list[str]]:
    _ = context
    ontology_candidates: list[str] = []
    if project is not None and len(project.strip()) > 0:
        ontology_candidates.append(project.strip())
    for entity in entities:
        cleaned = entity.strip()
        if len(cleaned) > 0:
            ontology_candidates.append(cleaned)
    taxonomy_candidates: list[str] = []
    for tag in tags:
        cleaned = tag.strip()
        if len(cleaned) > 0:
            taxonomy_candidates.append(cleaned)
    return {
        "ontology_candidates": _unique_values(ontology_candidates),
        "taxonomy_candidates": _unique_values(taxonomy_candidates),
    }


def normalize_candidates(
    ontology_candidates: list[str],
    taxonomy_candidates: list[str],
    *,
    context: dict[str, Any],
) -> dict[str, list[str]]:
    _ = context
    return {
        "ontology_candidates": _unique_values(ontology_candidates),
        "taxonomy_candidates": _unique_values(taxonomy_candidates),
    }


def emit_ontology_globals(
    ontology_candidates: list[str],
    taxonomy_candidates: list[str],
    *,
    context: dict[str, Any],
) -> dict[str, list[str]]:
    _ = context
    return {
        "ontology_candidates": _unique_values(ontology_candidates),
        "taxonomy_candidates": _unique_values(taxonomy_candidates),
    }


def _unique_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = " ".join(value.split()).strip()
        if len(key) == 0:
            continue
        lowered = key.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(key)
    return result
