#!/bin/sh
set -eu

COMPOSE_FILE="docker-compose.integration.yml"

cleanup() {
  docker compose -f "$COMPOSE_FILE" down -v
}

trap cleanup EXIT

docker compose -f "$COMPOSE_FILE" up -d
sleep 12

export MEA_RUN_INTEGRATION_TESTS=1
export MEA_INTEGRATION_DATABASE_URL="postgresql://memory_agents:memory_agents@127.0.0.1:5434/memory_agents_test"
export MEA_INTEGRATION_QDRANT_URL="http://127.0.0.1:6334"

uv run python -m unittest tests.test_phase2_integration tests.test_phase3_integration tests.test_phase4_integration
