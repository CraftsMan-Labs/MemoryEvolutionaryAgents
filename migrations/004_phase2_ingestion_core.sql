CREATE TABLE IF NOT EXISTS canonical_memories (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL,
  source_path TEXT NOT NULL,
  file_path TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  project TEXT,
  problem TEXT,
  solution TEXT,
  event_date TEXT,
  extraction_confidence DOUBLE PRECISION NOT NULL,
  tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  entities JSONB NOT NULL DEFAULT '[]'::jsonb,
  obsidian_note_path TEXT,
  qdrant_point_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_id, file_path, content_hash)
);

CREATE TABLE IF NOT EXISTS memory_chunks (
  id BIGSERIAL PRIMARY KEY,
  memory_id BIGINT NOT NULL REFERENCES canonical_memories(id) ON DELETE CASCADE,
  chunk_id TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  start_offset INTEGER NOT NULL,
  end_offset INTEGER NOT NULL,
  vector_size INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (memory_id, chunk_id)
);

CREATE TABLE IF NOT EXISTS workflow_stage_events (
  id BIGSERIAL PRIMARY KEY,
  run_id BIGINT NOT NULL,
  file_run_id BIGINT NOT NULL,
  source_id BIGINT NOT NULL,
  file_path TEXT NOT NULL,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  error_code TEXT,
  error_message TEXT,
  recorded_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_canonical_memories_source_id ON canonical_memories(source_id);
CREATE INDEX IF NOT EXISTS idx_workflow_stage_events_run_id ON workflow_stage_events(run_id);
