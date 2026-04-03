from __future__ import annotations

from .contracts import CitationRecord, RetrievalResultRecord


class ChatSynthesisService:
    def synthesize_answer(
        self,
        query: str,
        vector_results: list[RetrievalResultRecord],
        linkwalk_results: list[RetrievalResultRecord],
        top_k: int,
    ) -> tuple[str, float, list[CitationRecord]]:
        merged = self._merge_results(vector_results, linkwalk_results)
        top_results = merged[:top_k]
        if len(top_results) == 0:
            answer = (
                "I could not find matching memories for this query under the current "
                "filters. Try relaxing filters or adding more context."
            )
            return (answer, 0.0, [])

        lines = [f"Answer for query: {query}"]
        for index, result in enumerate(top_results, start=1):
            snippet = result.snippet.replace("\n", " ").strip()
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            lines.append(f"{index}. {snippet}")
        answer = "\n".join(lines)

        score_total = sum(result.normalized_score for result in top_results)
        confidence = min(1.0, score_total / max(1, len(top_results)))

        citations: list[CitationRecord] = []
        seen: set[tuple[str, str | None, str | None]] = set()
        for result in top_results:
            key = (result.source_path, result.note_path, result.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                CitationRecord(
                    source_path=result.source_path,
                    note_path=result.note_path,
                    chunk_id=result.chunk_id,
                )
            )
        return (answer, confidence, citations)

    def _merge_results(
        self,
        vector_results: list[RetrievalResultRecord],
        linkwalk_results: list[RetrievalResultRecord],
    ) -> list[RetrievalResultRecord]:
        by_memory: dict[int, RetrievalResultRecord] = {}
        for result in [*vector_results, *linkwalk_results]:
            existing = by_memory.get(result.memory_id)
            if existing is None or result.normalized_score > existing.normalized_score:
                by_memory[result.memory_id] = result
        merged = list(by_memory.values())
        merged.sort(
            key=lambda item: (item.normalized_score, item.score, -item.memory_id),
            reverse=True,
        )
        return merged
