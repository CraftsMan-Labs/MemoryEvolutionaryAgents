from __future__ import annotations

import re
from collections import deque
from pathlib import Path

from .contracts import LinkWalkCandidate, LinkWalkRequest, LinkWalkResponse

_WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:#[^\]]+)?(?:\|[^\]]+)?\]\]")


class ObsidianLinkGraphReader:
    def __init__(self, vault_path: str) -> None:
        self._vault_path = Path(vault_path)

    def walk(self, request: LinkWalkRequest) -> LinkWalkResponse:
        graph = self._build_graph()
        if len(graph) == 0:
            return LinkWalkResponse(candidates=[])

        queue: deque[tuple[str, int]] = deque()
        visited: set[str] = set()
        candidates: list[LinkWalkCandidate] = []

        for seed in request.seed_note_paths:
            resolved_seed = self._resolve_seed(seed, graph)
            if resolved_seed is None:
                continue
            queue.append((resolved_seed, 0))

        while len(queue) > 0:
            note_path, depth = queue.popleft()
            if note_path in visited:
                continue
            visited.add(note_path)
            candidates.append(LinkWalkCandidate(note_path=note_path, depth=depth))
            if depth >= request.max_depth:
                continue
            neighbors = graph.get(note_path, [])
            for neighbor in neighbors[: request.max_fanout]:
                if neighbor in visited:
                    continue
                queue.append((neighbor, depth + 1))

        return LinkWalkResponse(candidates=candidates)

    def _build_graph(self) -> dict[str, list[str]]:
        if self._vault_path.exists() is False:
            return {}
        markdown_files = list(self._vault_path.rglob("*.md"))
        name_to_path: dict[str, str] = {}
        for markdown_file in markdown_files:
            canonical = str(markdown_file.resolve())
            name_to_path[markdown_file.stem.lower()] = canonical
            relative = markdown_file.resolve().relative_to(self._vault_path.resolve())
            name_to_path[str(relative).lower()] = canonical

        graph: dict[str, list[str]] = {}
        for markdown_file in markdown_files:
            canonical = str(markdown_file.resolve())
            raw_links = self._extract_links(markdown_file)
            resolved_links: list[str] = []
            for raw_link in raw_links:
                candidate = name_to_path.get(raw_link.lower())
                if candidate is None:
                    continue
                if candidate == canonical:
                    continue
                if candidate in resolved_links:
                    continue
                resolved_links.append(candidate)
            graph[canonical] = resolved_links
        return graph

    def _extract_links(self, note_path: Path) -> list[str]:
        text = note_path.read_text(encoding="utf-8")
        matches = _WIKI_LINK_PATTERN.findall(text)
        links: list[str] = []
        for match in matches:
            compact = match.strip()
            if len(compact) == 0:
                continue
            links.append(compact)
        return links

    def _resolve_seed(
        self,
        seed_note_path: str,
        graph: dict[str, list[str]],
    ) -> str | None:
        seed = Path(seed_note_path)
        if seed.is_absolute():
            candidate = str(seed.resolve())
        else:
            candidate = str((self._vault_path / seed).resolve())
        if candidate in graph:
            return candidate
        return None
