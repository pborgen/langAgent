# LangChain Autonomous Agent Example

This repo now includes a minimal autonomous-style LangChain agent:

- file: `backend/agent_example.py`
- style: tool-calling loop (plan -> act -> observe -> repeat)
- goal: complete a user objective and stop by calling a `finish` tool

## Setup

1. Create and activate a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set your OpenAI key:

```bash
cp .env.example .env
# then edit .env and set OPENAI_API_KEY
```

Startup validation flags:

- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `STRICT_STARTUP_VALIDATION` (default: `false`)

## Repo Structure

- `backend/`: FastAPI API, LangGraph agent, ingestion scripts, and backend tests
- `frontend/`: React + TanStack frontend
- `docs/`: planning and implementation docs

## Run

```bash
python -m backend.agent_example "Create a file called notes/todo.txt with 3 project ideas."
```

Optional flags:

- `--model gpt-4o-mini`
- `--max-steps 15`

## What It Can Do

The example agent has a small toolset:

- `list_files(path=".")`
- `read_text(path)`
- `write_text(path, content)`
- `finish(answer)`

It is intentionally constrained to this project directory for safety.

## Customer Support Agent (LangGraph)

This repo also includes a SaaS-style customer support agent scaffold:

- file: `backend/customer_support_agent.py`
- API: `backend/support_api.py`
- sample docs: `backend/knowledge_base/*.txt`

Core features implemented:

- RAG-style answers over uploaded docs (local retriever + Pinecone option)
- LangGraph routing: docs answer vs tools vs escalate
- Tool calling for order status + appointment booking + escalation
- Session memory through LangGraph checkpointer
- Human-in-the-loop flow (`awaiting_human_approval` -> `/approve`)

### Run CLI demo

```bash
python3 -m backend.customer_support_agent "Where is order 1001?" --session-id s1 --customer-id c1
python3 -m backend.customer_support_agent "Customer threatens legal action" --session-id s2 --customer-id c2
python3 -m backend.customer_support_agent "Please escalate this issue" --session-id s2 --customer-id c2 --approve
```

### Use Pinecone for RAG

1. Set env vars in `.env`:

```bash
USE_PINECONE=true
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=...
PINECONE_NAMESPACE=support-kb
EMBEDDING_MODEL=text-embedding-3-small
```

2. Index your local docs into Pinecone:

```bash
python3 -m backend.index_kb_pinecone --index "$PINECONE_INDEX_NAME" --namespace "$PINECONE_NAMESPACE"
```

3. Run the support agent normally (it auto-switches to Pinecone when `USE_PINECONE=true`).

### Run API

```bash
uvicorn backend.support_api:app --reload
```

### Frontend (React + Vite + TanStack)

Install and run frontend in dev mode:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL (dev):

```text
http://127.0.0.1:5173/
```

Frontend routes:

- `/chat`
- `/settings`
- `/analytics`

Backend URL:

```text
http://127.0.0.1:8000
```

Build frontend for production and serve it from FastAPI `/`:

```bash
cd frontend
npm run build
cd ..
uvicorn backend.support_api:app --reload
```

Example requests:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"shop-1","customer_id":"cust-7","message":"Track order 1002"}'

curl -X POST http://127.0.0.1:8000/approve \
  -H "Content-Type: application/json" \
  -d '{"session_id":"shop-1","customer_id":"cust-7","message":"Approve escalation"}'
```

Frontend-facing v1 API:

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/messages \
  -H "Content-Type: application/json" \
  -d '{"session_id":"shop-1","customer_id":"cust-7","message":"Track order 1002"}'

curl -X POST http://127.0.0.1:8000/v1/escalations/approve \
  -H "Content-Type: application/json" \
  -d '{"session_id":"shop-1","customer_id":"cust-7","message":"Approve escalation"}'

curl http://127.0.0.1:8000/v1/sessions/shop-1/messages
curl "http://127.0.0.1:8000/v1/analytics/summary?session_id=shop-1"
```

Ingestion contract endpoints (MVP schema):

```bash
curl http://127.0.0.1:8000/v1/uploads/contract
curl -X POST http://127.0.0.1:8000/v1/uploads/jobs \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"tenant-1","filename":"faq.pdf","content_type":"application/pdf","source":"dashboard","storage_uri":"s3://bucket/tenant-1/faq.pdf"}'
```

## Tests

Backend:

```bash
pytest -q backend/tests
```

Docker vLLM integration test (opt-in, expensive):

```bash
RUN_DOCKER_INTEGRATION=1 \
VLLM_DOCKER_ENV_FILE=scripts/vllm/.env.docker.local \
pytest -q backend/tests/test_vllm_docker_integration.py
```

Frontend smoke checks:

```bash
cd frontend
npm run test
```

## Local vLLM Setup (Automated)

Use the automation scripts in `scripts/vllm/`.

0. (Ubuntu) install system dependencies:

```bash
sudo scripts/vllm/bootstrap_system_deps.sh --with-redis
```

1. Install vLLM into a dedicated virtualenv:

```bash
scripts/vllm/setup_vllm.sh
```

2. (Optional) pre-download a model:

```bash
scripts/vllm/download_model.sh --model Qwen/Qwen2.5-7B-Instruct
```

3. Start OpenAI-compatible local API server:

```bash
scripts/vllm/start_server.sh --model Qwen/Qwen2.5-7B-Instruct --port 8001
```

4. Run smoke test:

```bash
scripts/vllm/smoke_test.sh --api-base http://127.0.0.1:8001 --model Qwen/Qwen2.5-7B-Instruct
```

One-command bootstrap + run:

```bash
scripts/vllm/run_all.sh --model Qwen/Qwen2.5-7B-Instruct
```

Docker one-command startup:

```bash
scripts/vllm/docker_up.sh
```

### GPU/CPU Auto Detection

`scripts/vllm/start_server.sh` auto-detects runtime:

- NVIDIA GPU present (`nvidia-smi` works) -> starts with `--device cuda`
- Otherwise -> starts with `--device cpu`

Override manually if needed:

```bash
scripts/vllm/start_server.sh --device cuda
scripts/vllm/start_server.sh --device cpu
```

### Remote Access From Other Machines

Start server in public mode and protect it with an API key:

```bash
scripts/vllm/start_server.sh \
  --model Qwen/Qwen2.5-7B-Instruct \
  --public \
  --api-key "replace-with-strong-key"
```

Then open firewall port (Ubuntu UFW):

```bash
sudo ufw allow 8001/tcp
```

From another machine:

```bash
curl http://<GPU_MACHINE_IP>:8001/v1/models \
  -H "Authorization: Bearer replace-with-strong-key"
```

### Redis Memory Proxy (Persistent Context)

`vLLM` itself is stateless. To keep conversation context across requests, run the Redis-backed proxy:

```bash
scripts/vllm/start_memory_proxy.sh \
  --host 0.0.0.0 \
  --port 8010 \
  --redis-url redis://127.0.0.1:6379/0 \
  --vllm-api-base http://127.0.0.1:8001 \
  --vllm-model Qwen/Qwen2.5-7B-Instruct \
  --vllm-api-key "replace-with-strong-key" \
  --proxy-api-key "replace-with-strong-key"
```

Call from another machine (same `session_id` keeps memory):

```bash
curl -X POST http://<GPU_MACHINE_IP>:8010/chat \
  -H "Authorization: Bearer replace-with-strong-key" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","message":"My name is Paul"}'

curl -X POST http://<GPU_MACHINE_IP>:8010/chat \
  -H "Authorization: Bearer replace-with-strong-key" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","message":"What is my name?"}'
```

Inspect or clear session memory:

```bash
curl http://<GPU_MACHINE_IP>:8010/sessions/demo-1/messages \
  -H "Authorization: Bearer replace-with-strong-key"

curl -X DELETE http://<GPU_MACHINE_IP>:8010/sessions/demo-1/messages \
  -H "Authorization: Bearer replace-with-strong-key"
```

### Run vLLM As systemd User Service

Install + start persistent background service:

```bash
scripts/vllm/install_user_service.sh \
  --model Qwen/Qwen2.5-7B-Instruct \
  --api-key "replace-with-strong-key"
```

Useful service commands:

```bash
systemctl --user status vllm.service
systemctl --user restart vllm.service
journalctl --user -u vllm.service -f
```

Optional: keep service running even when not logged in:

```bash
sudo loginctl enable-linger "$USER"
```

Install memory proxy as a user service:

```bash
scripts/vllm/install_memory_proxy_user_service.sh \
  --proxy-api-key "replace-with-strong-key" \
  --vllm-api-key "replace-with-strong-key"
```

Manage memory proxy service:

```bash
systemctl --user status vllm-memory-proxy.service
systemctl --user restart vllm-memory-proxy.service
journalctl --user -u vllm-memory-proxy.service -f
```

## Production Notes

- Add ingestion pipeline for uploads (PDF/HTML/Docs) instead of static `backend/knowledge_base/*.txt`.
- Replace demo tools with real integrations (Shopify/Stripe/Google Calendar/helpdesk).
- Add auth, rate limiting, tenant isolation, and billing (Stripe) before production use.

## Planning Docs

- `docs/README.md`
- `docs/PROJECT_GOALS.md`
- `docs/ARCHITECTURE_AND_STANDARDS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/EXECUTION_PLAN.md`
- `docs/FEATURE_BACKLOG.md`
- `docs/SPRINT_1_BOARD.md`
