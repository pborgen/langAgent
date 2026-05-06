# Scripts

Automation scripts for local development and operations live under this directory.

## Available Groups

- `vllm/`: local `vLLM` setup, model serving, Redis memory proxy, and systemd user service installers.

## Quick Start

From repo root:

```bash
scripts/vllm/bootstrap_system_deps.sh --with-redis
scripts/vllm/setup_vllm.sh
scripts/vllm/start_server.sh --public --api-key "replace-with-strong-key"
scripts/vllm/start_memory_proxy.sh --proxy-api-key "replace-with-strong-key" --vllm-api-key "replace-with-strong-key"
```

For full command details, see `scripts/vllm/README.md`.

## Docker Shortcut

```bash
scripts/vllm/docker_up.sh
```

This starts `vLLM + Redis + memory proxy` via Docker Compose.
