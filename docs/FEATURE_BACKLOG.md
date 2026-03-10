# Feature Backlog

Priorities:

- P0: required for paid pilot readiness
- P1: important growth features
- P2: post-pilot optimizations

## P0 Features

### F-001 Multi-Tenant Auth + Isolation
User story:
As a business owner, I need my data isolated from other businesses.

Acceptance criteria:

- All API requests are tenant-scoped.
- Conversations, docs, and integrations cannot be cross-accessed.
- Unauthorized cross-tenant access attempts are blocked and logged.

### F-002 Document Upload + Indexing
User story:
As a business owner, I need to upload FAQs and docs so the agent can answer accurately.

Acceptance criteria:

- Upload endpoint accepts text/PDF/HTML (or initial subset).
- Upload job chunks and indexes content in tenant namespace.
- Indexing status is visible and failures are retryable.

### F-003 Source-Grounded RAG Answers
User story:
As a support user, I need answers grounded in business docs.

Acceptance criteria:

- Agent uses retrieved context for doc-based responses.
- Retrieval metadata (source/chunk) is available for debugging.
- Low-confidence responses trigger safe fallback or escalation.

### F-004 Real Order Lookup Integration
User story:
As a customer, I want accurate live order status.

Acceptance criteria:

- Agent queries real order provider for tenant store.
- Failure scenarios return helpful fallback and escalation option.
- API credentials are validated and encrypted.

### F-005 Google Calendar Booking
User story:
As a customer, I want to book support/demo appointments automatically.

Acceptance criteria:

- Agent creates valid events in configured calendar.
- Booking conflicts are handled gracefully.
- Confirmation payload includes date/time/timezone details.

### F-006 Human Escalation Inbox
User story:
As a human operator, I need to review and resolve escalated conversations quickly.

Acceptance criteria:

- Escalations are listed with priority and summary.
- Operator can approve, respond, and mark resolved.
- Conversation history is visible in escalation view.

### F-007 Billing With Stripe
User story:
As a business owner, I need to subscribe and manage plans.

Acceptance criteria:

- Trial and paid subscriptions supported.
- Webhooks update subscription state correctly.
- Plan limits are enforced in product.

## P1 Features

### F-008 Website Embed Widget
User story:
As a business owner, I need an easy chat widget for my site.

Acceptance criteria:

- Script snippet can be embedded on external sites.
- Widget connects securely to tenant backend.
- Basic theming options are available.

### F-009 Email Channel Support
User story:
As a support team, I need agent responses over email.

Acceptance criteria:

- Inbound email creates/continues conversation threads.
- Agent responses can be sent back via provider integration.
- Escalation flow works for email-origin threads.

### F-010 Analytics Dashboard
User story:
As a business owner, I need visibility into support performance.

Acceptance criteria:

- Dashboard shows volume, resolution rate, and escalations.
- Metrics filter by date range and channel.
- Exportable summary is available for reporting.

## P2 Features

### F-011 Agency White-Label Mode
### F-012 A/B Prompt and Routing Experiments
### F-013 Advanced Retrieval Evaluation Harness
### F-014 SLA/Queue Management For Human Agents

## Recommended Build Order

1. F-001, F-002, F-003
2. F-004, F-005
3. F-006, F-007
4. F-008, F-009, F-010
5. P2 features

## Backlog Governance

- Every feature must have:
  - clear owner
  - acceptance criteria
  - test plan
  - rollout plan
- No feature moves to implementation without a P0/P1/P2 priority and DoD.
