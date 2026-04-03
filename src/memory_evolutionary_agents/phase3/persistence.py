from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from psycopg.types.json import Json

from ..phase2.persistence import PostgresConnectionFactory
from .contracts import (
    ProposalStatus,
    ProposalType,
    RegistryStatus,
    RegistryTermRecord,
    RelationRecord,
    SchemaProposalRecord,
    SchemaProposalStateEventRecord,
)
from .errors import ProposalNotFoundError


class SchemaProposalCreateRequest:
    def __init__(
        self,
        proposal_type: ProposalType,
        candidate_value: str,
        normalized_value: str,
        confidence: float,
        context: dict[str, Any],
        idempotency_key: str,
        linked_record_id: int | None,
    ) -> None:
        self.proposal_type = proposal_type
        self.candidate_value = candidate_value
        self.normalized_value = normalized_value
        self.confidence = confidence
        self.context = context
        self.idempotency_key = idempotency_key
        self.linked_record_id = linked_record_id


class Phase3Repository:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def list_ontology_terms(self) -> list[RegistryTermRecord]:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, normalized_name, status, merged_into_term_id
                    FROM ontology_terms
                    """
                )
                rows = cast(list[dict[str, Any]], cur.fetchall())
        return [_registry_term_from_row(row, "merged_into_term_id") for row in rows]

    def list_taxonomy_tags(self) -> list[RegistryTermRecord]:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, normalized_name, status, merged_into_tag_id
                    FROM taxonomy_tags
                    """
                )
                rows = cast(list[dict[str, Any]], cur.fetchall())
        return [_registry_term_from_row(row, "merged_into_tag_id") for row in rows]

    def find_ontology_term_by_normalized(
        self, normalized_name: str
    ) -> RegistryTermRecord | None:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, normalized_name, status, merged_into_term_id
                    FROM ontology_terms
                    WHERE normalized_name = %s
                    """,
                    (normalized_name,),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            return None
        return _registry_term_from_row(row, "merged_into_term_id")

    def find_taxonomy_tag_by_normalized(
        self, normalized_name: str
    ) -> RegistryTermRecord | None:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, normalized_name, status, merged_into_tag_id
                    FROM taxonomy_tags
                    WHERE normalized_name = %s
                    """,
                    (normalized_name,),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            return None
        return _registry_term_from_row(row, "merged_into_tag_id")

    def get_ontology_term_by_id(self, term_id: int) -> RegistryTermRecord | None:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, normalized_name, status, merged_into_term_id
                    FROM ontology_terms
                    WHERE id = %s
                    """,
                    (term_id,),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            return None
        return _registry_term_from_row(row, "merged_into_term_id")

    def get_taxonomy_tag_by_id(self, tag_id: int) -> RegistryTermRecord | None:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, normalized_name, status, merged_into_tag_id
                    FROM taxonomy_tags
                    WHERE id = %s
                    """,
                    (tag_id,),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            return None
        return _registry_term_from_row(row, "merged_into_tag_id")

    def upsert_ontology_term(
        self, name: str, status: RegistryStatus
    ) -> RegistryTermRecord:
        normalized_name = _normalize_value(name)
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ontology_terms(name, normalized_name, status)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (normalized_name) DO UPDATE
                    SET name = EXCLUDED.name,
                        status = CASE
                            WHEN ontology_terms.status = 'approved' THEN ontology_terms.status
                            ELSE EXCLUDED.status
                        END,
                        updated_at = NOW()
                    RETURNING id, name, normalized_name, status, merged_into_term_id
                    """,
                    (name, normalized_name, status.value),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            raise RuntimeError("failed to upsert ontology term")
        merged_into_term_id = cast(int | None, row["merged_into_term_id"])
        return RegistryTermRecord(
            id=cast(int, row["id"]),
            name=str(row["name"]),
            normalized_name=str(row["normalized_name"]),
            status=RegistryStatus(str(row["status"])),
            merged_into_id=merged_into_term_id,
        )

    def upsert_taxonomy_tag(
        self, name: str, status: RegistryStatus
    ) -> RegistryTermRecord:
        normalized_name = _normalize_value(name)
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO taxonomy_tags(name, normalized_name, status)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (normalized_name) DO UPDATE
                    SET name = EXCLUDED.name,
                        status = CASE
                            WHEN taxonomy_tags.status = 'approved' THEN taxonomy_tags.status
                            ELSE EXCLUDED.status
                        END,
                        updated_at = NOW()
                    RETURNING id, name, normalized_name, status, merged_into_tag_id
                    """,
                    (name, normalized_name, status.value),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            raise RuntimeError("failed to upsert taxonomy tag")
        merged_into_tag_id = cast(int | None, row["merged_into_tag_id"])
        return RegistryTermRecord(
            id=cast(int, row["id"]),
            name=str(row["name"]),
            normalized_name=str(row["normalized_name"]),
            status=RegistryStatus(str(row["status"])),
            merged_into_id=merged_into_tag_id,
        )

    def upsert_relation(
        self,
        source_term_id: int,
        predicate: str,
        target_term_id: int,
        status: RegistryStatus,
    ) -> RelationRecord:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO relations(source_term_id, predicate, target_term_id, status)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (source_term_id, predicate, target_term_id) DO UPDATE
                    SET status = EXCLUDED.status,
                        updated_at = NOW()
                    RETURNING id, source_term_id, predicate, target_term_id, status
                    """,
                    (source_term_id, predicate, target_term_id, status.value),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            raise RuntimeError("failed to upsert relation")
        return RelationRecord(
            id=cast(int, row["id"]),
            source_term_id=cast(int, row["source_term_id"]),
            predicate=str(row["predicate"]),
            target_term_id=cast(int, row["target_term_id"]),
            status=RegistryStatus(str(row["status"])),
        )

    def create_or_update_proposal(
        self, request: SchemaProposalCreateRequest
    ) -> SchemaProposalRecord:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO schema_proposals(
                      proposal_type,
                      candidate_value,
                      normalized_value,
                      confidence,
                      status,
                      context,
                      idempotency_key,
                      linked_record_id,
                      merged_into_record_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (idempotency_key) DO UPDATE
                    SET confidence = EXCLUDED.confidence,
                        context = EXCLUDED.context,
                        linked_record_id = EXCLUDED.linked_record_id,
                        updated_at = NOW()
                    RETURNING id, proposal_type, candidate_value, normalized_value,
                              confidence, status, context, linked_record_id,
                              merged_into_record_id, created_at, updated_at
                    """,
                    (
                        request.proposal_type.value,
                        request.candidate_value,
                        request.normalized_value,
                        request.confidence,
                        ProposalStatus.PROVISIONAL.value,
                        Json(request.context),
                        request.idempotency_key,
                        request.linked_record_id,
                        None,
                    ),
                )
                row = cur.fetchone()
        if row is None:
            raise RuntimeError("failed to create schema proposal")
        return _proposal_from_row(row)

    def list_proposals(
        self,
        status: ProposalStatus | None,
        proposal_type: ProposalType | None,
        limit: int,
    ) -> list[SchemaProposalRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = %s")
            params.append(status.value)
        if proposal_type is not None:
            clauses.append("proposal_type = %s")
            params.append(proposal_type.value)
        where_clause = ""
        if len(clauses) > 0:
            where_clause = "WHERE " + " AND ".join(clauses)
        params.append(limit)

        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                query = f"""
                    SELECT id, proposal_type, candidate_value, normalized_value,
                           confidence, status, context, linked_record_id,
                           merged_into_record_id, created_at, updated_at
                    FROM schema_proposals
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s
                    """
                cur.execute(cast(Any, query), tuple(params))
                rows = cast(list[dict[str, Any]], cur.fetchall())
        return [_proposal_from_row(row) for row in rows]

    def get_proposal(self, proposal_id: int) -> SchemaProposalRecord:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, proposal_type, candidate_value, normalized_value,
                           confidence, status, context, linked_record_id,
                           merged_into_record_id, created_at, updated_at
                    FROM schema_proposals
                    WHERE id = %s
                    """,
                    (proposal_id,),
                )
                row = cast(dict[str, Any] | None, cur.fetchone())
        if row is None:
            raise ProposalNotFoundError(f"proposal not found: {proposal_id}")
        return _proposal_from_row(row)

    def list_proposal_events(
        self, proposal_id: int
    ) -> list[SchemaProposalStateEventRecord]:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, proposal_id, from_status, to_status, changed_by, note, changed_at
                    FROM schema_proposal_state_events
                    WHERE proposal_id = %s
                    ORDER BY changed_at ASC
                    """,
                    (proposal_id,),
                )
                rows = cast(list[dict[str, Any]], cur.fetchall())
        events: list[SchemaProposalStateEventRecord] = []
        for row in rows:
            from_status_value = row["from_status"]
            events.append(
                SchemaProposalStateEventRecord(
                    id=cast(int, row["id"]),
                    proposal_id=cast(int, row["proposal_id"]),
                    from_status=(
                        ProposalStatus(str(from_status_value))
                        if from_status_value is not None
                        else None
                    ),
                    to_status=ProposalStatus(str(row["to_status"])),
                    changed_by=str(row["changed_by"]),
                    note=str(row["note"]) if row["note"] is not None else None,
                    changed_at=cast(datetime, row["changed_at"]),
                )
            )
        return events

    def update_proposal_status(
        self,
        proposal_id: int,
        to_status: ProposalStatus,
        changed_by: str,
        note: str | None,
        merged_into_record_id: int | None,
    ) -> SchemaProposalRecord:
        proposal = self.get_proposal(proposal_id)
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE schema_proposals
                    SET status = %s,
                        merged_into_record_id = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, proposal_type, candidate_value, normalized_value,
                              confidence, status, context, linked_record_id,
                              merged_into_record_id, created_at, updated_at
                    """,
                    (
                        to_status.value,
                        merged_into_record_id,
                        proposal_id,
                    ),
                )
                updated_row = cast(dict[str, Any] | None, cur.fetchone())
                cur.execute(
                    """
                    INSERT INTO schema_proposal_state_events(
                      proposal_id,
                      from_status,
                      to_status,
                      changed_by,
                      note
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        proposal_id,
                        proposal.status.value,
                        to_status.value,
                        changed_by,
                        note,
                    ),
                )
        if updated_row is None:
            raise RuntimeError(f"failed to update proposal status: {proposal_id}")
        return _proposal_from_row(updated_row)

    def update_ontology_term_status(
        self,
        term_id: int,
        status: RegistryStatus,
        merged_into_term_id: int | None,
    ) -> None:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE ontology_terms
                    SET status = %s,
                        merged_into_term_id = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status.value, merged_into_term_id, term_id),
                )

    def update_taxonomy_tag_status(
        self,
        tag_id: int,
        status: RegistryStatus,
        merged_into_tag_id: int | None,
    ) -> None:
        with self._connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE taxonomy_tags
                    SET status = %s,
                        merged_into_tag_id = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status.value, merged_into_tag_id, tag_id),
                )


def _normalize_value(value: str) -> str:
    return " ".join(value.lower().split())


def _registry_term_from_row(
    row: object,
    merged_column: str,
) -> RegistryTermRecord:
    record = cast(dict[str, Any], row)
    merged_value = record[merged_column]
    return RegistryTermRecord(
        id=int(record["id"]),
        name=str(record["name"]),
        normalized_name=str(record["normalized_name"]),
        status=RegistryStatus(str(record["status"])),
        merged_into_id=int(merged_value) if merged_value is not None else None,
    )


def _proposal_from_row(row: object) -> SchemaProposalRecord:
    record = cast(dict[str, Any], row)
    context_value = record["context"]
    context = context_value if isinstance(context_value, dict) else {}
    return SchemaProposalRecord(
        id=int(record["id"]),
        proposal_type=ProposalType(str(record["proposal_type"])),
        candidate_value=str(record["candidate_value"]),
        normalized_value=str(record["normalized_value"]),
        confidence=float(record["confidence"]),
        status=ProposalStatus(str(record["status"])),
        context=context,
        linked_record_id=(
            int(record["linked_record_id"])
            if record["linked_record_id"] is not None
            else None
        ),
        merged_into_record_id=(
            int(record["merged_into_record_id"])
            if record["merged_into_record_id"] is not None
            else None
        ),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )
