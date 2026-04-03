CREATE TABLE IF NOT EXISTS onboarding_state (
  id INTEGER PRIMARY KEY,
  is_completed BOOLEAN NOT NULL,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS connector_settings (
  id INTEGER PRIMARY KEY,
  obsidian_vault_path TEXT NOT NULL,
  qdrant_mode TEXT NOT NULL CHECK (qdrant_mode IN ('local_docker', 'external')),
  external_qdrant_url TEXT,
  external_qdrant_api_key_encrypted TEXT,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

INSERT INTO onboarding_state(id, is_completed, completed_at, created_at, updated_at)
VALUES(1, FALSE, NULL, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;
