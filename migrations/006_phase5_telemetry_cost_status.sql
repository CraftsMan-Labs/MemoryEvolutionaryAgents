CREATE TABLE IF NOT EXISTS model_pricing (
  id BIGSERIAL PRIMARY KEY,
  provider TEXT NOT NULL,
  model_name TEXT NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USD',
  input_cost_per_1k_tokens NUMERIC(14, 8) NOT NULL,
  output_cost_per_1k_tokens NUMERIC(14, 8) NOT NULL,
  effective_from TIMESTAMPTZ NOT NULL,
  effective_to TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (provider, model_name, effective_from)
);

CREATE TABLE IF NOT EXISTS token_usage_events (
  id BIGSERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  run_id BIGINT,
  request_id TEXT,
  correlation_id TEXT NOT NULL,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  provider TEXT NOT NULL,
  model_name TEXT NOT NULL,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens INTEGER NOT NULL DEFAULT 0,
  pricing_version_id BIGINT REFERENCES model_pricing(id),
  cost_amount NUMERIC(14, 6),
  currency TEXT,
  error_classification TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  recorded_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_model_pricing_lookup
  ON model_pricing(provider, model_name, effective_from DESC);

CREATE INDEX IF NOT EXISTS idx_token_usage_events_recorded_at
  ON token_usage_events(recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_token_usage_events_run_id
  ON token_usage_events(run_id);

CREATE INDEX IF NOT EXISTS idx_token_usage_events_request_id
  ON token_usage_events(request_id);
