from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
from pathlib import Path
from uuid import UUID

import httpx

from .contracts import (
    ObsidianWriteRequest,
    ObsidianWriteResponse,
    QdrantUpsertRequest,
    QdrantUpsertResponse,
)
from .errors import AdapterError


class QdrantAdapter(ABC):
    @abstractmethod
    def upsert(self, request: QdrantUpsertRequest) -> QdrantUpsertResponse:
        raise NotImplementedError


class HttpQdrantAdapter(QdrantAdapter):
    def __init__(
        self, base_url: str, collection_name: str, api_key: str | None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._collection_name = collection_name
        self._api_key = api_key

    def upsert(self, request: QdrantUpsertRequest) -> QdrantUpsertResponse:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key is not None:
            headers["api-key"] = self._api_key
        payload = {
            "points": [
                {
                    "id": _to_qdrant_point_id(point.point_id),
                    "vector": point.vector,
                    "payload": point.payload,
                }
                for point in request.points
            ]
        }
        url = f"{self._base_url}/collections/{self._collection_name}/points"
        try:
            response = httpx.put(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AdapterError(f"qdrant upsert failed: {exc}") from exc
        return QdrantUpsertResponse(
            stored_point_ids=[point.point_id for point in request.points]
        )


def _to_qdrant_point_id(raw_id: str) -> int | str:
    if raw_id.isdigit():
        return int(raw_id)
    try:
        UUID(raw_id)
        return raw_id
    except ValueError:
        digest = hashlib.sha256(raw_id.encode("utf-8")).digest()
        candidate = int.from_bytes(digest[:8], byteorder="big", signed=False)
        return max(candidate, 1)


class ObsidianAdapter(ABC):
    @abstractmethod
    def write_summary(self, request: ObsidianWriteRequest) -> ObsidianWriteResponse:
        raise NotImplementedError


class FileSystemObsidianAdapter(ObsidianAdapter):
    def __init__(self, vault_path: str) -> None:
        self._vault_path = Path(vault_path)

    def write_summary(self, request: ObsidianWriteRequest) -> ObsidianWriteResponse:
        summaries_root = self._vault_path / "memory-agent-summaries"
        summaries_root.mkdir(parents=True, exist_ok=True)
        file_name = Path(request.file_path).name.replace(" ", "_")
        if file_name.lower().endswith(".md"):
            safe_name = Path(file_name).stem
        else:
            safe_name = file_name
        summary_path = summaries_root / f"{safe_name}.md"
        content = f"# {request.title}\n\n{request.body}\n"
        summary_path.write_text(content, encoding="utf-8")
        return ObsidianWriteResponse(note_path=str(summary_path))
