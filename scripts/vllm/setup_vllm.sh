#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv-vllm}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
  cat <<'EOF'
Usage: scripts/vllm/setup_vllm.sh [--venv-dir PATH] [--python BIN]

Creates a dedicated virtualenv and installs vLLM + helpers.

Examples:
  scripts/vllm/setup_vllm.sh
  scripts/vllm/setup_vllm.sh --venv-dir .venv-vllm --python python3.11
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv-dir)
      VENV_DIR="$2"
      shift 2
      ;;
    --python)
      PYTHON_BIN="$2"
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

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python interpreter not found: $PYTHON_BIN" >&2
  exit 1
fi

echo "==> Creating virtualenv at: $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

echo "==> Activating virtualenv"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "==> Upgrading pip toolchain"
pip install --upgrade pip setuptools wheel

echo "==> Installing vLLM and supporting tools"
pip install --upgrade vllm huggingface_hub "uvicorn[standard]" fastapi

echo "==> Install complete"
echo "Activate with: source \"$VENV_DIR/bin/activate\""
