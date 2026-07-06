# Querio - Epic & Story Backlog
### Derived from SRD v1.4

Status legend:
- `Done` = implemented in the repo
- `In progress` = partially implemented or implemented but still being hardened
- `Pending` = not meaningfully started yet

---

## Epic 1 - Guardrail-Validated SQL Generation

Stories:
- 1.1 FastAPI `/ask` endpoint
- 1.2 Postgres with proper read-only execution model
- 1.3 Schema introspection tool
- 1.4 Pydantic AI SQL generator
- 1.5 Standalone SQL validator
- 1.6 Malicious-query blocking tests
- 1.7 Validator -> execution -> answer flow
- 1.8 Clarification flow
- 1.9 Unit/integration coverage for the core path

Current status:
- `Done`: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9
- `In progress`: 1.2

Notes:
- Read-only behavior is enforced transactionally today.
- Prompt guardrails and one bounded SQL repair retry were added as hardening work beyond the original plan.

---

## Epic 2 - Model Provider Abstraction

Stories:
- 2.1 Define provider abstraction
- 2.2 Claude path conforms to it
- 2.3 OpenAI path
- 2.4 Ollama path
- 2.5 Env-config switch
- 2.6 Proof that the same question works across providers

Current status:
- `Done`: 2.1, 2.2, 2.3, 2.4, 2.5
- `In progress`: 2.6

Notes:
- Architecture is provider-agnostic in code.
- The polished proof/demo flow across all providers still needs to be formalized.

---

## Epic 3 - Chat Frontend + Chart Rendering

Stories:
- 3.1 React chat scaffold
- 3.2 Wire UI to `/ask`
- 3.3 Shared answer/chart contract
- 3.4 Bar chart support
- 3.5 Line chart support
- 3.6 Histogram/distribution support
- 3.7 Graceful no-chart path
- 3.8 Clarification rendering
- 3.9 Friendly loading/error states

Current status:
- `Done`: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7, 3.8, 3.9
- `In progress`: 3.6

Notes:
- The current demo path clearly supports the main bar/line chart workflow.

---

## Epic 4 - Data Seeding & dbt Transformation

Stories:
- 4.1 Load Olist-style raw data
- 4.2 dbt project setup
- 4.3 Order fact model
- 4.4 Customer or product dimension model
- 4.5 Point the agent at marts instead of raw

Current status:
- `Done`: 4.2, 4.3, 4.4, 4.5
- `In progress`: 4.1

Notes:
- The main local flow currently uses deterministic synthetic Olist-shaped data instead of real CSV ingestion as the default path.
- dbt tests are now part of the local flow, which is ahead of the original minimal plan.

---

## Epic 5 - Observability, Testing & Polish

Stories:
- 5.1 Structured logging
- 5.2 Lightweight tracing
- 5.3 Coverage reporting
- 5.4 CI pipeline
- 5.5 Strong README/docs
- 5.6 Demo GIF / showcase artifacts

Current status:
- `Done`: 5.1, 5.5
- `In progress`: 5.3, 5.4
- `Pending`: 5.2, 5.6

Notes:
- Logging is in good shape.
- Repo documentation has improved substantially, but final presentation polish is still a separate task.

---

## Epic 6 - Data Platform Extension

Stories:
- 6.1 Airflow refresh DAG
- 6.2 Synthetic new-orders generator
- 6.3 Expand dbt layer
- 6.4 Add dbt test coverage
- 6.5 Kubernetes manifests
- 6.6 Validate locally on cluster
- 6.7 Keep the extension clearly separated in docs

Current status:
- `Done`: 6.1, 6.2, 6.4, 6.7
- `In progress`: 6.3
- `Pending`: 6.5, 6.6

Notes:
- This extension exists, but should still be framed as secondary to the core agent story.

---

## Suggested Next Focus

1. Finish hardening the provider-proof story in Epic 2.
2. Tighten the remaining read-only-role/security gap in Epic 1.
3. Decide whether histogram support is worth finishing or whether the current chart scope is sufficient.
4. Keep Epic 6 clearly secondary unless applying for a more infra-heavy role.
