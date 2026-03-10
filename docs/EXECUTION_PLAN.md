# Execution Plan (March-May 2026)

This is the actionable implementation plan for shipping a paid-pilot-ready Customer Support Agent SaaS.

## Timeline

- Sprint 1: March 9, 2026 - March 20, 2026
- Sprint 2: March 23, 2026 - April 3, 2026
- Sprint 3: April 6, 2026 - April 17, 2026
- Sprint 4: April 20, 2026 - May 1, 2026
- Sprint 5: May 4, 2026 - May 15, 2026
- Sprint 6: May 18, 2026 - May 29, 2026

## Sprint 1: Foundation + Quality Baseline

Goals:

- Stabilize current backend/frontend flows
- Add test and logging baseline
- Prepare for multi-tenant work

Tasks:

- Add API tests for `/chat`, `/approve`, health, and error paths
- Add frontend smoke checks for `/chat`, `/settings`, `/analytics`
- Add structured logging for route decision, tools used, and latency
- Create environment validation on startup

Exit criteria:

- Core test suite green in CI
- Agent decisions traceable in logs
- Local dev setup documented and reproducible

## Sprint 2: Knowledge Upload + Indexing MVP

Goals:

- Replace static docs-only flow with upload-driven ingestion

Tasks:

- Build tenant-scoped upload endpoint
- Implement chunking and ingestion workers
- Index content in Pinecone namespace per tenant
- Add upload status view in frontend settings/admin section

Exit criteria:

- Tenant can upload docs and query new knowledge in chat
- Failed indexing jobs can be retried
- Source metadata is visible in logs/debug output

## Sprint 3: Tenant Isolation + Security

Goals:

- Enforce multi-tenant data boundaries and secure integrations

Tasks:

- Add auth middleware and tenant resolution
- Add tenant scoping to conversations, docs, and tools
- Encrypt integration credentials at rest
- Add audit logs for access failures and escalation approvals

Exit criteria:

- Cross-tenant access blocked in tests
- Credential handling passes security checklist
- Tenant context enforced in all primary API routes

## Sprint 4: Real Integrations

Goals:

- Move from demo tools to real business actions

Tasks:

- Integrate Shopify (or first chosen order provider) order lookup
- Integrate Google Calendar booking tool
- Add integration setup + validation endpoints
- Expand tool error handling and human fallback behavior

Exit criteria:

- Live order status lookups return correct production-like responses
- Calendar bookings create valid events with IDs
- Integration health checks visible in settings UI

## Sprint 5: Human Operations + Billing

Goals:

- Complete human handoff operations and monetization path

Tasks:

- Build escalation inbox/operator UI
- Add escalation approve/resolve workflow with history
- Integrate Stripe subscriptions and webhook processing
- Enforce plan limits in backend middleware

Exit criteria:

- Human agents can resolve escalated cases end-to-end
- Trial and paid plan lifecycle works
- Plan limits are enforced and tested

## Sprint 6: Pilot Readiness + Launch Prep

Goals:

- Hardening for first paying pilot customers

Tasks:

- Load/performance test key chat and tool flows
- Add monitoring dashboards and alerting
- Run reliability and incident-response drills
- Finalize onboarding flow and pilot documentation

Exit criteria:

- Performance targets met under expected pilot load
- On-call and incident runbook complete
- Pilot onboarding checklist complete

## Cross-Sprint Workstreams

- Prompt/routing evaluation set maintenance
- Cost monitoring (tokens, vector queries, integration calls)
- Weekly backlog reprioritization (`FEATURE_BACKLOG.md`)
- Weekly risk review and mitigation tracking

## Immediate Next 7 Days (Starting March 4, 2026)

1. Add backend test harness and first 10 API/agent tests.
2. Add structured logging fields for route, tool, latency, and status.
3. Add startup config validation for required env vars.
4. Define upload API contract and first ingestion job schema.
5. Create Sprint 1 board with owners and estimates.

## Execution Progress Update (March 4, 2026)

Completed in codebase:

- Backend test harness added with API and routing tests (`backend/tests/`).
- Structured logging added in API and agent turn flow.
- Startup config loading/validation added (`backend/app_config.py` + API lifespan checks).
- Upload API contract and ingestion job schema endpoints added (`/v1/uploads/...`).
- Frontend smoke route test scaffolding added (Vitest route checks).

Remaining:

- Create Sprint 1 task board with owners/estimates.
- Install project dependencies in local environment and run full test suite.

## Definition Of Execution Complete (Pilot Gate)

- Multi-tenant isolation verified
- Upload-to-RAG pipeline operating in production-like flow
- Real order and calendar integrations live
- Human escalation workflow operational
- Stripe billing and plan enforcement active
- Monitoring + incident response in place
