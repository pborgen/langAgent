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

Frontend smoke checks:

```bash
cd frontend
npm run test
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
