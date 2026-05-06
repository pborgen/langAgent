#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-7B-Instruct}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"
VENV_DIR="${VENV_DIR:-.venv-vllm}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${SERVICE_DIR}/vllm.service"
ENV_FILE="${SERVICE_DIR}/vllm.env"
API_KEY="${API_KEY:-change-me}"
ENABLE_LINGER="${ENABLE_LINGER:-false}"

usage() {
  cat <<'EOF'
Usage: scripts/vllm/install_user_service.sh [options]

Installs and enables a systemd --user service for vLLM.

Options:
  --model MODEL
  --host HOST
  --port PORT
  --venv-dir PATH
  --api-key KEY
  --enable-linger
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
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
    --venv-dir)
      VENV_DIR="$2"
      shift 2
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --enable-linger)
      ENABLE_LINGER="true"
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

mkdir -p "$SERVICE_DIR"

cat > "$ENV_FILE" <<EOF
VLLM_MODEL=$MODEL
VLLM_HOST=$HOST
VLLM_PORT=$PORT
VLLM_VENV_DIR=$VENV_DIR
VLLM_API_KEY=$API_KEY
EOF

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=vLLM OpenAI API Server (user)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=%h/.config/systemd/user/vllm.env
WorkingDirectory=$ROOT_DIR
ExecStart=$ROOT_DIR/scripts/vllm/start_server.sh --venv-dir \${VLLM_VENV_DIR} --model \${VLLM_MODEL} --host \${VLLM_HOST} --port \${VLLM_PORT} --api-key \${VLLM_API_KEY} --public
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now vllm.service

if [[ "$ENABLE_LINGER" == "true" ]]; then
  loginctl enable-linger "$USER"
fi

echo "==> Installed and started user service: vllm.service"
echo "Check status: systemctl --user status vllm.service"
echo "Logs:        journalctl --user -u vllm.service -f"
