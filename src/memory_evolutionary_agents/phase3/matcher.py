from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .contracts import RegistryStatus, RegistryTermRecord


@dataclass(frozen=True)
class MatchResult:
    matched: RegistryTermRecord | None
    confidence: float


class OntologyMatcherService:
    def __init__(self, threshold: float) -> None:
        self._threshold = threshold

    def match(self, candidate: str, registry: list[RegistryTermRecord]) -> MatchResult:
        normalized_candidate = _normalize_value(candidate)
        if len(normalized_candidate) == 0:
            return MatchResult(matched=None, confidence=0.0)

        best: RegistryTermRecord | None = None
        best_score = 0.0
        for record in registry:
            if record.status in {RegistryStatus.REJECTED, RegistryStatus.MERGED}:
                continue
            score = _similarity(normalized_candidate, record.normalized_name)
            if score > best_score:
                best = record
                best_score = score

        if best is None:
            return MatchResult(matched=None, confidence=0.0)
        if best_score < self._threshold:
            return MatchResult(matched=None, confidence=best_score)
        return MatchResult(matched=best, confidence=best_score)


def _similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    return float(SequenceMatcher(a=left, b=right).ratio())


def _normalize_value(value: str) -> str:
    return " ".join(value.lower().split())
