from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from .contracts import TelemetrySpanEvent
from .errors import TelemetryAdapterError


class TelemetryAdapter(ABC):
    @abstractmethod
    def emit_span(self, event: TelemetrySpanEvent) -> None:
        raise NotImplementedError


class NoopTelemetryAdapter(TelemetryAdapter):
    def emit_span(self, event: TelemetrySpanEvent) -> None:
        _ = event


class LangfuseTelemetryAdapter(TelemetryAdapter):
    def __init__(
        self,
        base_url: str,
        public_key: str,
        secret_key: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._public_key = public_key
        self._secret_key = secret_key
        self._timeout_seconds = timeout_seconds

    def emit_span(self, event: TelemetrySpanEvent) -> None:
        payload = {
            "batch": [
                {
                    "id": f"{event.trace_id}:{event.span_name}",
                    "type": "span-create",
                    "timestamp": event.started_at.isoformat(),
                    "body": {
                        "traceId": event.trace_id,
                        "name": event.span_name,
                        "startTime": event.started_at.isoformat(),
                        "endTime": event.ended_at.isoformat(),
                        "metadata": event.metadata,
                        "level": event.status,
                    },
                }
            ]
        }
        try:
            response = httpx.post(
                f"{self._base_url}/api/public/ingestion",
                auth=(self._public_key, self._secret_key),
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TelemetryAdapterError(f"langfuse emission failed: {exc}") from exc
