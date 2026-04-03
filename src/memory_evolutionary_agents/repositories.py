from __future__ import annotations

from datetime import datetime, timezone

from .contracts import (
    ConnectorConfigRecord,
    FileRunRecord,
    FileSnapshot,
    IngestionRunRecord,
    OnboardingStateRecord,
    QdrantMode,
    SourceRecord,
    SourceState,
)
from .database import Database


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _row_id(value: int | None) -> int:
    if value is None:
        raise RuntimeError("database did not return a row id")
    return value


class SourceRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create(self, path: str) -> SourceRecord:
        now = _utc_now()
        with self._database.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sources(path, state, created_at, updated_at, last_scan_file_count, last_scan_error_count)
                VALUES(?, ?, ?, ?, 0, 0)
                """,
                (path, SourceState.ACTIVE.value, now, now),
            )
            source_id = _row_id(cursor.lastrowid)
            row = conn.execute(
                "SELECT * FROM sources WHERE id = ?", (source_id,)
            ).fetchone()
        return SourceRecord.model_validate(dict(row))

    def patch(
        self, source_id: int, path: str | None, state: SourceState | None
    ) -> SourceRecord:
        updates: list[str] = []
        values: list[object] = []
        if state is not None:
            updates.append("state = ?")
            values.append(state.value)
        if path is not None:
            updates.append("path = ?")
            values.append(path)
        if len(updates) == 0:
            raise ValueError("patch request must include at least one field")
        updates.append("updated_at = ?")
        values.append(_utc_now())
        values.append(source_id)

        with self._database.connection() as conn:
            cursor = conn.execute(
                f"UPDATE sources SET {', '.join(updates)} WHERE id = ?",
                tuple(values),
            )
            if cursor.rowcount == 0:
                raise ValueError("source not found")
            row = conn.execute(
                "SELECT * FROM sources WHERE id = ?", (source_id,)
            ).fetchone()
        return SourceRecord.model_validate(dict(row))

    def list_all(self) -> list[SourceRecord]:
        with self._database.connection() as conn:
            rows = conn.execute("SELECT * FROM sources ORDER BY id ASC").fetchall()
        return [SourceRecord.model_validate(dict(row)) for row in rows]

    def list_active(self) -> list[SourceRecord]:
        with self._database.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sources WHERE state = ? ORDER BY id ASC",
                (SourceState.ACTIVE.value,),
            ).fetchall()
        return [SourceRecord.model_validate(dict(row)) for row in rows]

    def set_scan_status(
        self,
        source_id: int,
        error: str | None,
        scanned_files: int,
        scan_errors: int,
    ) -> None:
        now = _utc_now()
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE sources
                SET last_scan_at = ?, last_error = ?, last_scan_file_count = ?, last_scan_error_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, error, scanned_files, scan_errors, now, source_id),
            )


class RunRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def start_run(self) -> IngestionRunRecord:
        now = _utc_now()
        with self._database.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO ingestion_runs(started_at, status) VALUES(?, ?)",
                (now, "running"),
            )
            run_id = _row_id(cursor.lastrowid)
            row = conn.execute(
                "SELECT * FROM ingestion_runs WHERE id = ?", (run_id,)
            ).fetchone()
        return IngestionRunRecord.model_validate(dict(row))

    def finish_run(
        self, run_id: int, discovered: int, queued: int, failed: int
    ) -> IngestionRunRecord:
        now = _utc_now()
        status = "failed" if failed > 0 else "completed"
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE ingestion_runs
                SET ended_at = ?, status = ?, total_discovered = ?, total_queued = ?, total_failed = ?
                WHERE id = ?
                """,
                (now, status, discovered, queued, failed, run_id),
            )
            row = conn.execute(
                "SELECT * FROM ingestion_runs WHERE id = ?", (run_id,)
            ).fetchone()
        return IngestionRunRecord.model_validate(dict(row))

    def get_run(self, run_id: int) -> IngestionRunRecord:
        with self._database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM ingestion_runs WHERE id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise ValueError("run not found")
        return IngestionRunRecord.model_validate(dict(row))

    def list_runs(self, limit: int) -> list[IngestionRunRecord]:
        with self._database.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ingestion_runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [IngestionRunRecord.model_validate(dict(row)) for row in rows]

    def upsert_file_discovery(self, run_id: int, snapshot: FileSnapshot) -> None:
        with self._database.connection() as conn:
            existing = conn.execute(
                "SELECT id, last_fingerprint FROM ingested_files WHERE source_id = ? AND path = ?",
                (snapshot.source_id, snapshot.file_path),
            ).fetchone()

            status = "queued"
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO ingested_files(source_id, path, last_mtime_ns, content_hash, last_fingerprint, last_seen_run_id, updated_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.source_id,
                        snapshot.file_path,
                        snapshot.mtime_ns,
                        snapshot.content_hash,
                        snapshot.fingerprint,
                        run_id,
                        _utc_now(),
                    ),
                )
            elif existing["last_fingerprint"] != snapshot.fingerprint:
                conn.execute(
                    """
                    UPDATE ingested_files
                    SET last_mtime_ns = ?, content_hash = ?, last_fingerprint = ?, last_seen_run_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        snapshot.mtime_ns,
                        snapshot.content_hash,
                        snapshot.fingerprint,
                        run_id,
                        _utc_now(),
                        existing["id"],
                    ),
                )
            else:
                conn.execute(
                    "UPDATE ingested_files SET last_seen_run_id = ?, updated_at = ? WHERE id = ?",
                    (run_id, _utc_now(), existing["id"]),
                )
                status = "skipped"

            conn.execute(
                """
                INSERT INTO file_processing_runs(run_id, source_id, source_path, file_path, stage, status, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    snapshot.source_id,
                    snapshot.source_path,
                    snapshot.file_path,
                    "discovered",
                    status,
                    _utc_now(),
                ),
            )

    def mark_scan_error(
        self,
        run_id: int,
        source_id: int,
        source_path: str,
        error_code: str,
        error_message: str,
    ) -> None:
        with self._database.connection() as conn:
            conn.execute(
                """
                INSERT INTO file_processing_runs(run_id, source_id, source_path, file_path, stage, status, error_code, error_message, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    source_id,
                    source_path,
                    source_path,
                    "discovered",
                    "failed",
                    error_code,
                    error_message,
                    _utc_now(),
                ),
            )

    def list_file_runs_for_run(self, run_id: int) -> list[FileRunRecord]:
        with self._database.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM file_processing_runs WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
        return [FileRunRecord.model_validate(dict(row)) for row in rows]


class OnboardingRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_state(self) -> OnboardingStateRecord:
        with self._database.connection() as conn:
            row = conn.execute("SELECT * FROM onboarding_state WHERE id = 1").fetchone()
            if row is None:
                now = _utc_now()
                conn.execute(
                    """
                    INSERT INTO onboarding_state(id, is_completed, completed_at, created_at, updated_at)
                    VALUES(1, 0, NULL, ?, ?)
                    """,
                    (now, now),
                )
                row = conn.execute(
                    "SELECT * FROM onboarding_state WHERE id = 1"
                ).fetchone()
        return OnboardingStateRecord.model_validate(dict(row))

    def mark_completed(self) -> OnboardingStateRecord:
        now = _utc_now()
        with self._database.connection() as conn:
            conn.execute(
                """
                UPDATE onboarding_state
                SET is_completed = 1, completed_at = ?, updated_at = ?
                WHERE id = 1
                """,
                (now, now),
            )
            row = conn.execute("SELECT * FROM onboarding_state WHERE id = 1").fetchone()
        return OnboardingStateRecord.model_validate(dict(row))

    def upsert_connector_config(
        self,
        obsidian_vault_path: str,
        qdrant_mode: QdrantMode,
        external_qdrant_url: str | None,
        encrypted_api_key: str | None,
    ) -> ConnectorConfigRecord:
        now = _utc_now()
        with self._database.connection() as conn:
            row = conn.execute(
                "SELECT id FROM connector_settings WHERE id = 1"
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO connector_settings(
                      id,
                      obsidian_vault_path,
                      qdrant_mode,
                      external_qdrant_url,
                      external_qdrant_api_key_encrypted,
                      created_at,
                      updated_at
                    ) VALUES(1, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        obsidian_vault_path,
                        qdrant_mode.value,
                        external_qdrant_url,
                        encrypted_api_key,
                        now,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE connector_settings
                    SET obsidian_vault_path = ?, qdrant_mode = ?, external_qdrant_url = ?,
                        external_qdrant_api_key_encrypted = ?, updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        obsidian_vault_path,
                        qdrant_mode.value,
                        external_qdrant_url,
                        encrypted_api_key,
                        now,
                    ),
                )
            config_row = conn.execute(
                "SELECT * FROM connector_settings WHERE id = 1"
            ).fetchone()
        return ConnectorConfigRecord.model_validate(dict(config_row))

    def get_connector_config(self) -> ConnectorConfigRecord | None:
        with self._database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM connector_settings WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        return ConnectorConfigRecord.model_validate(dict(row))
