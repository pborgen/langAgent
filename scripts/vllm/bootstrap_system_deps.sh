#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/vllm/bootstrap_system_deps.sh [--with-nvidia] [--with-redis]

Installs baseline Ubuntu packages for local vLLM workflows.
Run with sudo (or as root).

Options:
  --with-nvidia    Also install NVIDIA utility package (does not install driver/CUDA toolkit)
  --with-redis     Install redis-server for chat memory persistence
EOF
}

WITH_NVIDIA="false"
WITH_REDIS="false"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-nvidia)
      WITH_NVIDIA="true"
      shift
      ;;
    --with-redis)
      WITH_REDIS="true"
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

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Please run as root. Example: sudo scripts/vllm/bootstrap_system_deps.sh" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "==> Updating apt index"
apt-get update

PACKAGES=(
  python3
  python3-venv
  python3-pip
  build-essential
  git
  curl
  jq
)

echo "==> Installing packages: ${PACKAGES[*]}"
apt-get install -y "${PACKAGES[@]}"

if [[ "$WITH_NVIDIA" == "true" ]]; then
  NVIDIA_UTILS_PACKAGE="$(apt-cache search '^nvidia-utils-[0-9]+' | awk '{print $1}' | sort -Vr | head -n1)"
  if [[ -n "$NVIDIA_UTILS_PACKAGE" ]]; then
    echo "==> Installing NVIDIA utility package: $NVIDIA_UTILS_PACKAGE"
    apt-get install -y "$NVIDIA_UTILS_PACKAGE"
  else
    echo "No nvidia-utils package found in apt repositories; skipping." >&2
  fi
fi

if [[ "$WITH_REDIS" == "true" ]]; then
  echo "==> Installing redis-server"
  apt-get install -y redis-server
  systemctl enable redis-server
  systemctl restart redis-server
fi

echo "==> System dependency bootstrap complete"
