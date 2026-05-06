#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-7B-Instruct}"
VENV_DIR="${VENV_DIR:-.venv-vllm}"
PORT="${PORT:-8001}"
HOST="${HOST:-127.0.0.1}"
DOWNLOAD_FIRST="${DOWNLOAD_FIRST:-false}"
PUBLIC_MODE="${PUBLIC_MODE:-false}"
API_KEY="${API_KEY:-}"
DEVICE="${DEVICE:-auto}"

usage() {
  cat <<'EOF'
Usage: scripts/vllm/run_all.sh [--model MODEL] [--download]

One-command flow:
  1) setup vLLM virtualenv and dependencies
  2) optionally download model snapshot
  3) start vLLM API server

Options:
  --model MODEL_ID_OR_PATH
  --venv-dir PATH
  --host HOST
  --port PORT
  --download
  --public
  --api-key KEY
  --device auto|cuda|cpu
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --venv-dir)
      VENV_DIR="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --download)
      DOWNLOAD_FIRST="true"
      shift
      ;;
    --public)
      PUBLIC_MODE="true"
      HOST="0.0.0.0"
      shift
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --device)
      DEVICE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$ROOT_DIR/scripts/vllm/setup_vllm.sh" --venv-dir "$VENV_DIR"

if [[ "$DOWNLOAD_FIRST" == "true" ]]; then
  "$ROOT_DIR/scripts/vllm/download_model.sh" --venv-dir "$VENV_DIR" --model "$MODEL"
fi

ARGS=(
  --venv-dir "$VENV_DIR"
  --model "$MODEL"
  --host "$HOST"
  --port "$PORT"
  --device "$DEVICE"
)

if [[ "$PUBLIC_MODE" == "true" ]]; then
  ARGS+=(--public)
fi

if [[ -n "$API_KEY" ]]; then
  ARGS+=(--api-key "$API_KEY")
fi

exec "$ROOT_DIR/scripts/vllm/start_server.sh" "${ARGS[@]}"
