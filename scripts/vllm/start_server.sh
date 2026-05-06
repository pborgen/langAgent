#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv-vllm}"
MODEL="${MODEL:-Qwen/Qwen2.5-7B-Instruct}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8001}"
DTYPE="${DTYPE:-auto}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
DEVICE="${DEVICE:-auto}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
API_KEY="${API_KEY:-}"
PUBLIC_MODE="${PUBLIC_MODE:-false}"
AUTO_DEVICE="${AUTO_DEVICE:-true}"

usage() {
  cat <<'EOF'
Usage: scripts/vllm/start_server.sh [options]

Starts vLLM OpenAI-compatible API server.

Options:
  --venv-dir PATH
  --model MODEL_OR_LOCAL_PATH
  --host HOST
  --port PORT
  --dtype DTYPE
  --max-model-len TOKENS
  --device auto|cuda|cpu
  --gpu-memory-utilization FLOAT
  --api-key KEY
  --public
  --no-auto-device

Examples:
  scripts/vllm/start_server.sh
  scripts/vllm/start_server.sh --model Qwen/Qwen2.5-7B-Instruct --port 8001
  scripts/vllm/start_server.sh --public --api-key "replace-me"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv-dir)
      VENV_DIR="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
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
    --dtype)
      DTYPE="$2"
      shift 2
      ;;
    --max-model-len)
      MAX_MODEL_LEN="$2"
      shift 2
      ;;
    --device)
      DEVICE="$2"
      shift 2
      ;;
    --gpu-memory-utilization)
      GPU_MEMORY_UTILIZATION="$2"
      shift 2
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --public)
      PUBLIC_MODE="true"
      HOST="0.0.0.0"
      shift
      ;;
    --no-auto-device)
      AUTO_DEVICE="false"
      shift
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

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Virtualenv not found at $VENV_DIR. Run setup_vllm.sh first." >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

if [[ "$AUTO_DEVICE" == "true" && "$DEVICE" == "auto" ]]; then
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    DEVICE="cuda"
  else
    DEVICE="cpu"
  fi
fi

echo "==> Starting vLLM server"
echo "Model: $MODEL"
echo "URL:   http://$HOST:$PORT"
echo "Device: $DEVICE"

ARGS=(
  --model "$MODEL"
  --host "$HOST"
  --port "$PORT"
  --dtype "$DTYPE"
  --max-model-len "$MAX_MODEL_LEN"
  --device "$DEVICE"
)

if [[ "$DEVICE" == "cuda" ]]; then
  ARGS+=(--gpu-memory-utilization "$GPU_MEMORY_UTILIZATION")
fi

if [[ -n "$API_KEY" ]]; then
  ARGS+=(--api-key "$API_KEY")
fi

if [[ "$PUBLIC_MODE" == "true" && -z "$API_KEY" ]]; then
  echo "WARNING: public mode is enabled without API key. This is not secure." >&2
fi

exec python -m vllm.entrypoints.openai.api_server "${ARGS[@]}"
