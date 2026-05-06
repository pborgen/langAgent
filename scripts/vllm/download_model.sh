#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv-vllm}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen2.5-7B-Instruct}"
TARGET_DIR="${TARGET_DIR:-models}"
REVISION="${REVISION:-main}"

usage() {
  cat <<'EOF'
Usage: scripts/vllm/download_model.sh [--model MODEL_ID] [--target-dir DIR] [--revision REV]

Downloads a Hugging Face model snapshot to a local directory.
If no model is provided, defaults to Qwen/Qwen2.5-7B-Instruct.

Examples:
  scripts/vllm/download_model.sh
  scripts/vllm/download_model.sh --model meta-llama/Llama-3.1-8B-Instruct
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv-dir)
      VENV_DIR="$2"
      shift 2
      ;;
    --model)
      MODEL_ID="$2"
      shift 2
      ;;
    --target-dir)
      TARGET_DIR="$2"
      shift 2
      ;;
    --revision)
      REVISION="$2"
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

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Virtualenv not found at $VENV_DIR. Run setup_vllm.sh first." >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

mkdir -p "$TARGET_DIR"
LOCAL_DIR="$TARGET_DIR/$(echo "$MODEL_ID" | tr '/' '__')"

echo "==> Downloading $MODEL_ID to $LOCAL_DIR"
python - <<'PY'
import os
from huggingface_hub import snapshot_download

model_id = os.environ["MODEL_ID"]
local_dir = os.environ["LOCAL_DIR"]
revision = os.environ["REVISION"]

snapshot_download(
    repo_id=model_id,
    local_dir=local_dir,
    revision=revision,
    local_dir_use_symlinks=False,
)
print(f"Downloaded model to: {local_dir}")
PY

echo "==> Model download complete"
