#!/bin/sh
set -eu

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"

for file in /migrations/*.sql; do
  name=$(basename "$file")
  already_applied=$(psql "$DATABASE_URL" -t -A -c "SELECT 1 FROM schema_migrations WHERE filename = '$name' LIMIT 1;")
  if [ "$already_applied" = "1" ]; then
    continue
  fi

  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$file"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "INSERT INTO schema_migrations(filename) VALUES('$name');"
done
