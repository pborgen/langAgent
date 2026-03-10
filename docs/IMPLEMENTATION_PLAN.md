# Implementation Plan

## Planning Horizon
This plan covers delivery from prototype to paid pilot readiness.

## Phase 0: Foundation Hardening
Status: In progress

Deliverables:

- Stabilize current API + frontend flows
- Normalize env/config handling
- Add baseline tests for routing and core API endpoints
- Add structured logging for agent decisions

Definition of done:

- Local development setup works from clean clone
- Automated tests run in CI for core paths
- Regression checklist documented

## Phase 1: Knowledge Ingestion MVP
Status: Planned

Deliverables:

- Tenant-specific document upload endpoint
- Chunking + embedding pipeline
- Indexing into Pinecone/Supabase namespaces per tenant
- Admin UI for upload status and indexed docs

Definition of done:

- Tenant can upload docs and query them in chat
- Retrieval shows correct source metadata in logs
- Failed indexing jobs are visible and retryable

## Phase 2: Real Integrations
Status: Planned

Deliverables:

- Real order lookup integration (Shopify first)
- Real Google Calendar appointment booking tool
- Integration credential storage + validation

Definition of done:

- Agent can execute real order lookup for connected stores
- Agent can create calendar events with traceable event IDs
- Integration setup validated via health-check endpoint

## Phase 3: Human Handoff + Operations
Status: Planned

Deliverables:

- Human escalation inbox view (basic operator console)
- Approval/override workflows for high-risk actions
- Handoff payload standards (context, history, recommended next step)

Definition of done:

- Every escalation produces a complete handoff object
- Operators can approve/resolve escalations in UI
- Escalation audit trail persisted per conversation

## Phase 4: Multi-Tenant SaaS + Billing
Status: Planned

Deliverables:

- Tenant/org management and authentication
- Usage metering (messages, active seats, integrations)
- Stripe subscriptions + plan enforcement

Definition of done:

- New business can self-serve sign-up and start trial
- Paid plan upgrades/downgrades work end-to-end
- Entitlements enforced by backend middleware

## Phase 5: Launch Readiness
Status: Planned

Deliverables:

- Reliability/load testing
- Security review and secret management hardening
- Monitoring dashboards and on-call runbook
- Public onboarding docs and pricing page content

Definition of done:

- Pilot customers onboarded successfully
- SLA and incident response process documented
- Launch checklist fully complete

## Execution Cadence

- Weekly planning: update priorities in `FEATURE_BACKLOG.md`
- Weekly demo: review completed features against DoD
- Weekly risk review: identify blockers, dependencies, and scope changes

## Dependencies And Risks

- External API rate limits and provider outages
- LLM cost/latency constraints under load
- Integration complexity differences per ecommerce platform
- Data privacy and tenant isolation requirements
