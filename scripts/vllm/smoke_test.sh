#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001}"
MODEL="${MODEL:-Qwen/Qwen2.5-7B-Instruct}"

usage() {
  cat <<'EOF'
Usage: scripts/vllm/smoke_test.sh [--api-base URL] [--model MODEL_NAME]

Runs a quick health + generation test against a vLLM OpenAI-compatible server.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base)
      API_BASE="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
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

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for smoke tests." >&2
  exit 1
fi

echo "==> Checking model listing endpoint"
curl -fsS "$API_BASE/v1/models" >/dev/null
echo "OK: /v1/models reachable"

echo "==> Running sample chat completion"
curl -fsS "$API_BASE/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Reply with exactly: vllm ok\"}],
    \"temperature\": 0,
    \"max_tokens\": 16
  }"

echo
echo "==> Smoke test complete"
