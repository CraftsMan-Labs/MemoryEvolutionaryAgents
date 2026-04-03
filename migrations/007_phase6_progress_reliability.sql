ALTER TABLE file_processing_runs
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS file_stage_events (
  id BIGSERIAL PRIMARY KEY,
  run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  file_run_id BIGINT NOT NULL REFERENCES file_processing_runs(id),
  source_id BIGINT NOT NULL REFERENCES sources(id),
  file_path TEXT NOT NULL,
  from_stage TEXT,
  to_stage TEXT NOT NULL,
  status TEXT NOT NULL,
  duration_ms INTEGER,
  error_code TEXT,
  error_message TEXT,
  recorded_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS file_retry_queue (
  id BIGSERIAL PRIMARY KEY,
  file_run_id BIGINT NOT NULL UNIQUE REFERENCES file_processing_runs(id),
  run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_id BIGINT NOT NULL REFERENCES sources(id),
  file_path TEXT NOT NULL,
  status TEXT NOT NULL,
  attempt_count INTEGER NOT NULL,
  max_attempts INTEGER NOT NULL,
  next_attempt_at TIMESTAMPTZ NOT NULL,
  last_error_code TEXT,
  last_error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_file_stage_events_file_run_id
  ON file_stage_events(file_run_id, recorded_at);

CREATE INDEX IF NOT EXISTS idx_file_retry_queue_due
  ON file_retry_queue(status, next_attempt_at);
