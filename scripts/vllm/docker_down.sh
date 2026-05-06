#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-gpu}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.docker.local"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$SCRIPT_DIR/.env.docker.example" "$ENV_FILE"
fi

if [[ "$MODE" == "cpu" ]]; then
  COMPOSE_FILE="$SCRIPT_DIR/docker-compose.cpu.yml"
else
  COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
echo "Stack stopped for mode: $MODE"
