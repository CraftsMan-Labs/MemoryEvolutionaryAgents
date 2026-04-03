CREATE TABLE IF NOT EXISTS sources (
  id BIGSERIAL PRIMARY KEY,
  path TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL CHECK (state IN ('active', 'paused', 'deleted')),
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  last_scan_at TIMESTAMPTZ,
  last_error TEXT,
  last_scan_file_count INTEGER NOT NULL DEFAULT 0,
  last_scan_error_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id BIGSERIAL PRIMARY KEY,
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  total_discovered INTEGER NOT NULL DEFAULT 0,
  total_queued INTEGER NOT NULL DEFAULT 0,
  total_failed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ingested_files (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES sources(id),
  path TEXT NOT NULL,
  last_mtime_ns BIGINT NOT NULL,
  content_hash TEXT NOT NULL,
  last_fingerprint TEXT NOT NULL,
  last_seen_run_id BIGINT REFERENCES ingestion_runs(id),
  updated_at TIMESTAMPTZ NOT NULL,
  UNIQUE (source_id, path)
);

CREATE TABLE IF NOT EXISTS file_processing_runs (
  id BIGSERIAL PRIMARY KEY,
  run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_id BIGINT NOT NULL REFERENCES sources(id),
  source_path TEXT NOT NULL,
  file_path TEXT NOT NULL,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  error_code TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sources_state ON sources(state);
CREATE INDEX IF NOT EXISTS idx_runs_status ON ingestion_runs(status);
CREATE INDEX IF NOT EXISTS idx_file_runs_run_id ON file_processing_runs(run_id);
