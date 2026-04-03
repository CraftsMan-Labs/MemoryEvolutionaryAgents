from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from psycopg.types.json import Json

from ..phase2.persistence import PostgresConnectionFactory
from .contracts import (
    ChunkTrendPoint,
    ModelPricingRecord,
    TelemetryEventRecord,
    TelemetryEventRequest,
    UsageTrendPoint,
)


class PricingRepository:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def find_effective_pricing(
        self,
        provider: str,
        model_name: str,
        at_time: datetime,
    ) -> ModelPricingRecord | None:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      id,
                      provider,
                      model_name,
                      currency,
                      input_cost_per_1k_tokens,
                      output_cost_per_1k_tokens,
                      effective_from,
                      effective_to
                    FROM model_pricing
                    WHERE provider = %s
                      AND model_name = %s
                      AND effective_from <= %s
                      AND (effective_to IS NULL OR effective_to > %s)
                    ORDER BY effective_from DESC
                    LIMIT 1
                    """,
                    (provider, model_name, at_time, at_time),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            return None
        return ModelPricingRecord.model_validate(row)


class TelemetryRepository:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def insert_event(
        self,
        request: TelemetryEventRequest,
        pricing_version_id: int | None,
        cost_amount: Decimal | None,
        currency: str | None,
    ) -> TelemetryEventRecord:
        total_tokens = request.input_tokens + request.output_tokens
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO token_usage_events(
                      event_type,
                      run_id,
                      request_id,
                      correlation_id,
                      stage,
                      status,
                      provider,
                      model_name,
                      input_tokens,
                      output_tokens,
                      total_tokens,
                      pricing_version_id,
                      cost_amount,
                      currency,
                      error_classification,
                      metadata,
                      recorded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING
                      id,
                      event_type,
                      run_id,
                      request_id,
                      correlation_id,
                      stage,
                      status,
                      provider,
                      model_name,
                      input_tokens,
                      output_tokens,
                      total_tokens,
                      pricing_version_id,
                      cost_amount,
                      currency,
                      error_classification,
                      metadata,
                      recorded_at
                    """,
                    (
                        request.event_type,
                        request.run_id,
                        request.request_id,
                        request.correlation_id,
                        request.stage,
                        request.status,
                        request.provider,
                        request.model_name,
                        request.input_tokens,
                        request.output_tokens,
                        total_tokens,
                        pricing_version_id,
                        cost_amount,
                        currency,
                        request.error_classification,
                        Json(request.metadata),
                        request.recorded_at,
                    ),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            raise RuntimeError("failed to persist telemetry event")
        return TelemetryEventRecord.model_validate(row)

    def usage_trend(self, range_days: int) -> list[UsageTrendPoint]:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      TO_CHAR(recorded_at::date, 'YYYY-MM-DD') AS date,
                      COALESCE(SUM(input_tokens), 0) AS input_tokens,
                      COALESCE(SUM(output_tokens), 0) AS output_tokens,
                      COALESCE(SUM(total_tokens), 0) AS total_tokens,
                      COALESCE(SUM(cost_amount), 0) AS cost_amount
                    FROM token_usage_events
                    WHERE recorded_at >= NOW() - (%s || ' days')::interval
                    GROUP BY recorded_at::date
                    ORDER BY recorded_at::date ASC
                    """,
                    (range_days,),
                )
                rows = cast(list[dict[str, Any]], cur.fetchall())
        return [UsageTrendPoint.model_validate(row) for row in rows]

    def chunk_creation_trend(self, range_days: int) -> list[ChunkTrendPoint]:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      TO_CHAR(d.day, 'YYYY-MM-DD') AS date,
                      COALESCE(c.chunks_created, 0) AS chunks_created,
                      COALESCE(m.memories_created, 0) AS memories_created
                    FROM (
                      SELECT generate_series(
                        (NOW() - (%s || ' days')::interval)::date,
                        NOW()::date,
                        INTERVAL '1 day'
                      ) AS day
                    ) d
                    LEFT JOIN (
                      SELECT created_at::date AS day, COUNT(*)::int AS chunks_created
                      FROM memory_chunks
                      WHERE created_at >= NOW() - (%s || ' days')::interval
                      GROUP BY created_at::date
                    ) c ON c.day = d.day::date
                    LEFT JOIN (
                      SELECT created_at::date AS day, COUNT(*)::int AS memories_created
                      FROM canonical_memories
                      WHERE created_at >= NOW() - (%s || ' days')::interval
                      GROUP BY created_at::date
                    ) m ON m.day = d.day::date
                    ORDER BY d.day ASC
                    """,
                    (range_days, range_days, range_days),
                )
                rows = cast(list[dict[str, Any]], cur.fetchall())
        return [ChunkTrendPoint.model_validate(row) for row in rows]

    def memory_chunk_totals(self) -> tuple[int, int]:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*)::int AS count FROM canonical_memories")
                memories_row = cast(dict[str, Any] | None, cur.fetchone())
                cur.execute("SELECT COUNT(*)::int AS count FROM memory_chunks")
                chunks_row = cast(dict[str, Any] | None, cur.fetchone())
        total_memories = 0 if memories_row is None else int(memories_row["count"])
        total_chunks = 0 if chunks_row is None else int(chunks_row["count"])
        return total_memories, total_chunks
