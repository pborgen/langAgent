#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-gpu}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.docker"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$SCRIPT_DIR/.env.docker.example" "$ENV_FILE"
  echo "Created $ENV_FILE from template. Update API keys before public use."
fi

if [[ "$MODE" == "cpu" ]]; then
  COMPOSE_FILE="$SCRIPT_DIR/docker-compose.cpu.yml"
else
  COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
fi

set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
echo "Stack is starting with mode: $MODE"
echo "vLLM API:      http://127.0.0.1:${VLLM_PORT}"
echo "Memory proxy:  http://127.0.0.1:${PROXY_PORT}"
