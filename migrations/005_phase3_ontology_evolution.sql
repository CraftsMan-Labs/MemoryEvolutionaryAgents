ALTER TABLE canonical_memories
  ADD COLUMN IF NOT EXISTS ontology_terms JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS taxonomy_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS relation_edges JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS ontology_terms (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  normalized_name TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  merged_into_term_id BIGINT REFERENCES ontology_terms(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS taxonomy_tags (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  normalized_name TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  merged_into_tag_id BIGINT REFERENCES taxonomy_tags(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS relations (
  id BIGSERIAL PRIMARY KEY,
  source_term_id BIGINT NOT NULL REFERENCES ontology_terms(id) ON DELETE CASCADE,
  predicate TEXT NOT NULL,
  target_term_id BIGINT NOT NULL REFERENCES ontology_terms(id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_term_id, predicate, target_term_id)
);

CREATE TABLE IF NOT EXISTS schema_proposals (
  id BIGSERIAL PRIMARY KEY,
  proposal_type TEXT NOT NULL,
  candidate_value TEXT NOT NULL,
  normalized_value TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  status TEXT NOT NULL,
  context JSONB NOT NULL DEFAULT '{}'::jsonb,
  idempotency_key TEXT NOT NULL UNIQUE,
  linked_record_id BIGINT,
  merged_into_record_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS schema_proposal_state_events (
  id BIGSERIAL PRIMARY KEY,
  proposal_id BIGINT NOT NULL REFERENCES schema_proposals(id) ON DELETE CASCADE,
  from_status TEXT,
  to_status TEXT NOT NULL,
  changed_by TEXT NOT NULL,
  note TEXT,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ontology_terms_status ON ontology_terms(status);
CREATE INDEX IF NOT EXISTS idx_taxonomy_tags_status ON taxonomy_tags(status);
CREATE INDEX IF NOT EXISTS idx_relations_status ON relations(status);
CREATE INDEX IF NOT EXISTS idx_schema_proposals_status ON schema_proposals(status);
