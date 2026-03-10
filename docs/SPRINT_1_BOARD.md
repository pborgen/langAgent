# Sprint 1 Board (March 9-20, 2026)

## Goal
Stabilize the current platform baseline with tests, logging, and configuration validation.

## Tasks

| ID | Task | Owner | Estimate | Dependency | Status |
|---|---|---|---|---|---|
| S1-01 | Add API tests for `/health`, `/chat`, `/approve` | TBD | 4h | None | Done |
| S1-02 | Add routing logic unit tests | TBD | 2h | None | Done |
| S1-03 | Add upload contract and ingestion job schema endpoints | TBD | 5h | None | Done |
| S1-04 | Add startup config validation module | TBD | 3h | None | Done |
| S1-05 | Add structured JSON logging (API + agent turns) | TBD | 4h | S1-04 | Done |
| S1-06 | Add frontend route smoke tests (`/chat`, `/settings`, `/analytics`) | TBD | 2h | None | Done (pending local npm deps install) |
| S1-07 | Run backend and frontend test suites in CI/local | TBD | 2h | S1-01, S1-02, S1-06 | In progress |
| S1-08 | Publish Sprint 1 verification checklist | TBD | 2h | S1-07 | Planned |

## Definition of Done

- Backend tests pass locally and in CI.
- Frontend smoke tests pass locally and in CI.
- Logs include route decision, tools used, and latency.
- Startup validation behavior is documented and verified.

## Notes

- Current blocker: local environment missing `pytest` and `vitest` runtime installs.
- Next action: install dependencies and run the full test suite.
