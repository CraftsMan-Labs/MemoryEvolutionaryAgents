from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def initialize(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  path TEXT NOT NULL UNIQUE,
                  state TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  last_scan_at TEXT,
                  last_error TEXT,
                  last_scan_file_count INTEGER NOT NULL DEFAULT 0,
                  last_scan_error_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS ingestion_runs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  started_at TEXT NOT NULL,
                  ended_at TEXT,
                  status TEXT NOT NULL,
                  total_discovered INTEGER NOT NULL DEFAULT 0,
                  total_queued INTEGER NOT NULL DEFAULT 0,
                  total_failed INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS ingested_files (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source_id INTEGER NOT NULL,
                  path TEXT NOT NULL,
                  last_mtime_ns INTEGER NOT NULL,
                  content_hash TEXT NOT NULL,
                  last_fingerprint TEXT NOT NULL,
                  last_seen_run_id INTEGER,
                  updated_at TEXT NOT NULL,
                  UNIQUE(source_id, path),
                  FOREIGN KEY(source_id) REFERENCES sources(id)
                );

                CREATE TABLE IF NOT EXISTS file_processing_runs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id INTEGER NOT NULL,
                  source_id INTEGER NOT NULL,
                  source_path TEXT NOT NULL,
                  file_path TEXT NOT NULL,
                  stage TEXT NOT NULL,
                  status TEXT NOT NULL,
                  error_code TEXT,
                  error_message TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT,
                  FOREIGN KEY(run_id) REFERENCES ingestion_runs(id),
                  FOREIGN KEY(source_id) REFERENCES sources(id)
                );

                CREATE TABLE IF NOT EXISTS file_stage_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id INTEGER NOT NULL,
                  file_run_id INTEGER NOT NULL,
                  source_id INTEGER NOT NULL,
                  file_path TEXT NOT NULL,
                  from_stage TEXT,
                  to_stage TEXT NOT NULL,
                  status TEXT NOT NULL,
                  duration_ms INTEGER,
                  error_code TEXT,
                  error_message TEXT,
                  recorded_at TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES ingestion_runs(id),
                  FOREIGN KEY(file_run_id) REFERENCES file_processing_runs(id),
                  FOREIGN KEY(source_id) REFERENCES sources(id)
                );

                CREATE TABLE IF NOT EXISTS file_retry_queue (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  file_run_id INTEGER NOT NULL UNIQUE,
                  run_id INTEGER NOT NULL,
                  source_id INTEGER NOT NULL,
                  file_path TEXT NOT NULL,
                  status TEXT NOT NULL,
                  attempt_count INTEGER NOT NULL,
                  max_attempts INTEGER NOT NULL,
                  next_attempt_at TEXT NOT NULL,
                  last_error_code TEXT,
                  last_error_message TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(file_run_id) REFERENCES file_processing_runs(id),
                  FOREIGN KEY(run_id) REFERENCES ingestion_runs(id),
                  FOREIGN KEY(source_id) REFERENCES sources(id)
                );

                CREATE INDEX IF NOT EXISTS idx_file_stage_events_file_run_id
                ON file_stage_events(file_run_id);

                CREATE INDEX IF NOT EXISTS idx_file_retry_queue_next_attempt
                ON file_retry_queue(status, next_attempt_at);
                
                CREATE TABLE IF NOT EXISTS onboarding_state (
                  id INTEGER PRIMARY KEY,
                  is_completed INTEGER NOT NULL,
                  completed_at TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS connector_settings (
                  id INTEGER PRIMARY KEY,
                  obsidian_vault_path TEXT NOT NULL,
                  qdrant_mode TEXT NOT NULL,
                  external_qdrant_url TEXT,
                  external_qdrant_api_key_encrypted TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(
                conn,
                table_name="sources",
                column_name="last_scan_file_count",
                column_spec="INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                conn,
                table_name="sources",
                column_name="last_scan_error_count",
                column_spec="INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                conn,
                table_name="file_processing_runs",
                column_name="error_code",
                column_spec="TEXT",
            )
            self._ensure_column(
                conn,
                table_name="file_processing_runs",
                column_name="updated_at",
                column_spec="TEXT",
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_spec: str,
    ) -> None:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing_columns = {row[1] for row in rows}
        if column_name in existing_columns:
            return
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_spec}")
