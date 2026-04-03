from __future__ import annotations

from typing import Any


def retrieve_vector_context(
    query: str,
    filters: dict[str, Any],
    vector_top_k: int,
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    _ = context
    return {
        "query": query,
        "filters": filters,
        "vector_top_k": vector_top_k,
        "results": [],
    }


def retrieve_linkwalk_context(
    query: str,
    filters: dict[str, Any],
    seed_note_paths: list[str],
    link_depth: int,
    link_fanout: int,
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    _ = context
    return {
        "query": query,
        "filters": filters,
        "seed_note_paths": seed_note_paths,
        "link_depth": link_depth,
        "link_fanout": link_fanout,
        "results": [],
    }


def synthesize_chat_answer(
    query: str,
    top_k: int,
    vector_results: list[dict[str, Any]],
    linkwalk_results: list[dict[str, Any]],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    _ = context
    return {
        "answer": f"Answer for query: {query}",
        "confidence": 0.0,
        "top_k": top_k,
        "vector_count": len(vector_results),
        "linkwalk_count": len(linkwalk_results),
        "citations": [],
    }
