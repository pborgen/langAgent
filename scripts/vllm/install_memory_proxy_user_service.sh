#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8010}"
VENV_DIR="${VENV_DIR:-.venv-vllm}"
REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
VLLM_API_BASE="${VLLM_API_BASE:-http://127.0.0.1:8001}"
VLLM_MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
VLLM_API_KEY="${VLLM_API_KEY:-change-me}"
PROXY_API_KEY="${PROXY_API_KEY:-change-me}"
MEMORY_MAX_MESSAGES="${MEMORY_MAX_MESSAGES:-20}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${SERVICE_DIR}/vllm-memory-proxy.service"
ENV_FILE="${SERVICE_DIR}/vllm-memory-proxy.env"

usage() {
  cat <<'EOF'
Usage: scripts/vllm/install_memory_proxy_user_service.sh [options]

Installs and enables a systemd --user service for Redis memory proxy.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --venv-dir) VENV_DIR="$2"; shift 2 ;;
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

mkdir -p "$SERVICE_DIR"

cat > "$ENV_FILE" <<EOF
VLLM_PROXY_HOST=$HOST
VLLM_PROXY_PORT=$PORT
VLLM_VENV_DIR=$VENV_DIR
REDIS_URL=$REDIS_URL
VLLM_API_BASE=$VLLM_API_BASE
VLLM_MODEL=$VLLM_MODEL
VLLM_API_KEY=$VLLM_API_KEY
PROXY_API_KEY=$PROXY_API_KEY
MEMORY_MAX_MESSAGES=$MEMORY_MAX_MESSAGES
EOF

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=vLLM Redis Memory Proxy (user)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=%h/.config/systemd/user/vllm-memory-proxy.env
WorkingDirectory=$ROOT_DIR
ExecStart=$ROOT_DIR/scripts/vllm/start_memory_proxy.sh --venv-dir \${VLLM_VENV_DIR} --host \${VLLM_PROXY_HOST} --port \${VLLM_PROXY_PORT} --redis-url \${REDIS_URL} --vllm-api-base \${VLLM_API_BASE} --vllm-model \${VLLM_MODEL} --vllm-api-key \${VLLM_API_KEY} --proxy-api-key \${PROXY_API_KEY} --memory-max-messages \${MEMORY_MAX_MESSAGES}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now vllm-memory-proxy.service

echo "==> Installed and started user service: vllm-memory-proxy.service"
echo "Check status: systemctl --user status vllm-memory-proxy.service"
echo "Logs:        journalctl --user -u vllm-memory-proxy.service -f"
