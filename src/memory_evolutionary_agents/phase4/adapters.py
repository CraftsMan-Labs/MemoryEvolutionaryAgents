from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from .contracts import QdrantScoredPoint, QdrantSearchRequest, QdrantSearchResponse
from .errors import Phase4AdapterError


class QdrantSearchAdapter(ABC):
    @abstractmethod
    def search(self, request: QdrantSearchRequest) -> QdrantSearchResponse:
        raise NotImplementedError


class HttpQdrantSearchAdapter(QdrantSearchAdapter):
    def __init__(
        self,
        base_url: str,
        collection_name: str,
        api_key: str | None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._collection_name = collection_name
        self._api_key = api_key

    def search(self, request: QdrantSearchRequest) -> QdrantSearchResponse:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key is not None:
            headers["api-key"] = self._api_key
        payload: dict[str, object] = {
            "query": request.vector,
            "limit": request.limit,
            "with_payload": True,
        }
        filter_object = _build_filter_object(request)
        if filter_object is not None:
            payload["filter"] = filter_object

        url = f"{self._base_url}/collections/{self._collection_name}/points/query"
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise Phase4AdapterError(
                f"qdrant search failed: {exc}; body={exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise Phase4AdapterError(f"qdrant search failed: {exc}") from exc

        response_payload = response.json()
        result = response_payload.get("result")
        if isinstance(result, dict):
            result = result.get("points")
        if isinstance(result, list) is False:
            raise Phase4AdapterError("qdrant search returned invalid result payload")
        points: list[QdrantScoredPoint] = []
        for raw_point in result:
            if isinstance(raw_point, dict) is False:
                continue
            payload_raw = raw_point.get("payload")
            payload_value = payload_raw if isinstance(payload_raw, dict) else {}
            point_id = str(raw_point.get("id"))
            score_raw = raw_point.get("score", 0.0)
            score = float(score_raw) if isinstance(score_raw, (int, float)) else 0.0
            points.append(
                QdrantScoredPoint(
                    point_id=point_id,
                    score=score,
                    payload=payload_value,
                )
            )
        return QdrantSearchResponse(points=points)


def _build_filter_object(request: QdrantSearchRequest) -> dict[str, object] | None:
    conditions: list[dict[str, object]] = []
    if request.project is not None:
        conditions.append(
            {
                "key": "project",
                "match": {"value": request.project},
            }
        )
    if len(request.tags) > 0:
        conditions.append(
            {
                "key": "tags",
                "match": {"any": request.tags},
            }
        )
    if len(request.ontology_terms) > 0:
        conditions.append(
            {
                "key": "ontology_terms",
                "match": {"any": request.ontology_terms},
            }
        )
    if len(request.taxonomy_tags) > 0:
        conditions.append(
            {
                "key": "taxonomy_tags",
                "match": {"any": request.taxonomy_tags},
            }
        )
    if len(conditions) == 0:
        return None
    return {"must": conditions}
