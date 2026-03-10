# Project Goals

## Product Name
SupportPilot (working name)

## Vision
Build a low-cost, high-quality AI support agent that helps small businesses provide fast customer support without requiring a large support team.

## Problem Statement
Small businesses are often priced out of enterprise support tools and do not have time to build custom automations. They need a support assistant that can answer product/order questions, handle scheduling, and escalate only when necessary.

## Target Users

- Small business owners
- Operations/support leads at small businesses
- Agencies serving multiple SMB clients (white-label use case)

## Core Jobs To Be Done

- Answer repetitive customer questions 24/7
- Resolve order status requests quickly
- Book support/demo appointments
- Escalate risky or complex requests to humans with context

## Product Goals (12-Month Horizon)

- Deliver a production-ready multi-tenant support agent with document-grounded answers.
- Reach reliable human-escalation workflows for high-risk requests.
- Support embed deployment on client websites.
- Enable paid SaaS subscriptions with self-serve onboarding.

## Non-Goals (Current Phase)

- Replacing full ticketing platforms (Zendesk-level feature parity)
- Building a full CRM
- Solving every support channel on day one (start with web chat + API)

## Success Metrics

- Resolution automation rate: >= 60% of conversations resolved without human handoff
- Response latency (p95): <= 4 seconds for common queries
- Escalation quality: >= 90% of escalations include actionable context
- Customer satisfaction (CSAT proxy): positive feedback on >= 80% of resolved chats
- Business metric: first paid pilot customer before broad launch

## Pricing + Monetization Targets

- Core SaaS tier: $29-$99/month per business
- Optional setup fee for integrations/onboarding
- Agency white-label package with per-client pricing
- Widget installation monetization for Shopify/Wix clients

## Current Build Status

- Implemented:
  - LangGraph routing and agent loop
  - Tool-calling scaffold (order lookup, booking, escalate)
  - Human-in-the-loop approval flow
  - Local + Pinecone retrieval path
  - FastAPI backend and React/TanStack frontend
- Not yet production-ready:
  - Real external integrations (Shopify, Google Calendar, Stripe)
  - Multi-tenant auth/isolation
  - Upload pipeline for customer documents
