#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv-vllm}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8010}"
REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
VLLM_API_BASE="${VLLM_API_BASE:-http://127.0.0.1:8001}"
VLLM_MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
VLLM_API_KEY="${VLLM_API_KEY:-}"
PROXY_API_KEY="${PROXY_API_KEY:-}"
MEMORY_MAX_MESSAGES="${MEMORY_MAX_MESSAGES:-20}"

usage() {
  cat <<'EOF'
Usage: scripts/vllm/start_memory_proxy.sh [options]

Starts Redis-backed FastAPI memory proxy in front of vLLM.

Options:
  --venv-dir PATH
  --host HOST
  --port PORT
  --redis-url URL
  --vllm-api-base URL
  --vllm-model MODEL
  --vllm-api-key KEY
  --proxy-api-key KEY
  --memory-max-messages N
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv-dir) VENV_DIR="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --redis-url) REDIS_URL="$2"; shift 2 ;;
    --vllm-api-base) VLLM_API_BASE="$2"; shift 2 ;;
    --vllm-model) VLLM_MODEL="$2"; shift 2 ;;
    --vllm-api-key) VLLM_API_KEY="$2"; shift 2 ;;
    --proxy-api-key) PROXY_API_KEY="$2"; shift 2 ;;
    --memory-max-messages) MEMORY_MAX_MESSAGES="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Virtualenv not found at $VENV_DIR. Run setup_vllm.sh first." >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

export REDIS_URL
export VLLM_API_BASE
export VLLM_MODEL
export VLLM_API_KEY
export PROXY_API_KEY
export MEMORY_MAX_MESSAGES

echo "==> Starting vLLM memory proxy on http://$HOST:$PORT"
exec uvicorn backend.app.vllm_memory_proxy:app --host "$HOST" --port "$PORT"
