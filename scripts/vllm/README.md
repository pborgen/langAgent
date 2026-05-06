# vLLM Scripts

This folder contains automation for running local `vLLM`, enabling remote access, and adding Redis-backed chat memory persistence.

## Scripts

- `bootstrap_system_deps.sh`: install Ubuntu apt dependencies (`--with-nvidia`, `--with-redis`).
- `setup_vllm.sh`: create virtualenv and install `vllm` + Python dependencies.
- `download_model.sh`: pre-download model snapshots from Hugging Face.
- `start_server.sh`: run the OpenAI-compatible `vLLM` server with GPU/CPU auto-detection.
- `smoke_test.sh`: verify `/v1/models` and `/v1/chat/completions`.
- `run_all.sh`: one-command setup + optional model download + server start.
- `install_user_service.sh`: install `vllm.service` under `systemd --user`.
- `start_memory_proxy.sh`: run FastAPI Redis memory proxy for session continuity.
- `install_memory_proxy_user_service.sh`: install memory proxy as `systemd --user` service.
- `docker_up.sh`: start Docker Compose stack (`gpu` default, or `cpu`).
- `docker_down.sh`: stop Docker Compose stack.
- `docker_logs.sh`: stream Docker Compose logs.

## Typical Flow

```bash
# 1) System dependencies
sudo scripts/vllm/bootstrap_system_deps.sh --with-redis

# 2) Python env and packages
scripts/vllm/setup_vllm.sh

# 3) Start vLLM API (public network + API key)
scripts/vllm/start_server.sh --public --api-key "replace-with-strong-key"

# 4) Start Redis memory proxy
scripts/vllm/start_memory_proxy.sh \
  --host 0.0.0.0 \
  --port 8010 \
  --vllm-api-base http://127.0.0.1:8001 \
  --vllm-api-key "replace-with-strong-key" \
  --proxy-api-key "replace-with-strong-key"
```

## Docker (Simple Startup)

```bash
# GPU mode (default)
scripts/vllm/docker_up.sh

# CPU mode
scripts/vllm/docker_up.sh cpu
```

First run creates `scripts/vllm/.env.docker.local` from `scripts/vllm/.env.docker.example`.
Update API keys there before exposing ports publicly.

Disable auth for local-only use:

```bash
# in scripts/vllm/.env.docker.local
VLLM_REQUIRE_AUTH=false
VLLM_API_KEY=
PROXY_API_KEY=
```

Then restart:

```bash
scripts/vllm/docker_down.sh
scripts/vllm/docker_up.sh
```

Stop and inspect logs:

```bash
scripts/vllm/docker_logs.sh
scripts/vllm/docker_down.sh
```

## Service Mode

```bash
scripts/vllm/install_user_service.sh --api-key "replace-with-strong-key"
scripts/vllm/install_memory_proxy_user_service.sh \
  --vllm-api-key "replace-with-strong-key" \
  --proxy-api-key "replace-with-strong-key"
```

## Notes

- `vLLM` is stateless; use the memory proxy for multi-request context by `session_id`.
- Use strong API keys when exposing services to other machines.
- Open firewall ports explicitly (for example, `8001` for `vLLM`, `8010` for proxy).
