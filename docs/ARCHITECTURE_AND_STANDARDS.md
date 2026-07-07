# Architecture And Standards

## Current Architecture

- Backend: FastAPI (`backend/app/support_api.py`)
- Agent Orchestration: LangGraph (`backend/app/customer_support_agent.py`)
- LLM Provider: OpenAI via LangChain (`langchain-openai`)
- Retrieval:
  - Local document fallback retriever
  - Pinecone vector retrieval option
- Frontend: React + Vite + TanStack (`frontend/`)

## Target Production Architecture

- Frontend:
  - React + TanStack Router + TanStack Query
  - Embedded widget distribution script for customer websites
- API Layer:
  - FastAPI app with versioned REST endpoints (`/v1/...`)
  - Auth middleware (JWT/session API keys)
- Agent Layer:
  - LangGraph state machine per conversation thread
  - Structured routing for `answer`, `tool_action`, `escalate`
- Data Layer:
  - Postgres for tenants/users/billing metadata
  - Pinecone or Supabase pgvector for knowledge embeddings
- Integrations:
  - Shopify/WooCommerce or custom order systems
  - Google Calendar for booking
  - Stripe for subscription billing

## Core Domain Objects

- `Tenant`: business account/workspace
- `KnowledgeDocument`: uploaded content metadata and source
- `ConversationThread`: customer-agent session container
- `Message`: user/agent/tool event records
- `Escalation`: human handoff record with reason/summary/priority
- `IntegrationCredential`: encrypted provider secrets per tenant
- `Subscription`: billing plan and status

## Engineering Standards

- API contracts:
  - Define request/response schemas with Pydantic models.
  - Keep stable versioned routes for frontend and integrators.
- Agent behavior:
  - Require deterministic routing for high-risk intents.
  - Never execute sensitive tool actions without confirmation/guardrails.
- Retrieval:
  - Store source metadata and chunk ids for citation/debugging.
  - Log retrieval misses and low-confidence responses.
- Security:
  - Enforce tenant isolation at query and storage layers.
  - Encrypt integration credentials at rest.
  - Never log raw secrets or payment data.
- Observability:
  - Log every agent turn with route/tool usage and latency.
  - Track escalation reasons and failure categories.

## Reliability + Quality Targets

- Tool-call success rate: >= 99% on supported integrations
- Agent route accuracy (simple vs escalate): >= 90% in evaluation set
- Uptime target for API: >= 99.5% after launch

## Testing Strategy

- Unit tests: routing logic, tool adapters, validation
- Integration tests: chat flow, escalation flow, vector retrieval
- End-to-end tests: frontend chat -> backend -> agent -> response
- Safety tests: escalation triggers, tool abuse prevention, tenant leakage checks
