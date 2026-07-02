# Software Requirements Document (SRD)
## Querio — Natural Language Data Analyst Chatbot (POC)
### *Talk to your data.*

**Version:** 1.3

**Author:** Ahmed Jahin Akif

**Status:** Draft — POC scope (core) + optional extension

**Purpose:** Personal portfolio project targeting Data Software Engineer role

**Changelog (v1.1 → v1.2):** Re-scoped after a vibe-check pass. Querio is now explicitly an **agentic AI engineering showcase**, not a data-platform showcase. Agent framework locked to Pydantic AI. Added a real multi-provider model-switching architecture (Claude / OpenAI / local via Ollama). Dropped Airflow and Kubernetes from scope. Kept dbt in a reduced form. Locked the demo dataset.

**Changelog (v1.2 → v1.3):** Added Section 13 — an optional, clearly-separated "Data Platform Extension" covering Airflow, fuller dbt, and Kubernetes. This does **not** change the core POC's scope, success criteria, or non-goals (Sections 3.1, 9, 12 are unchanged) — it's a stretch phase to build only if/when it's worth the extra time for a specific application.

---

## 1. Overview

**Querio** is a proof-of-concept tool that lets a non-technical user ask a business question in plain English and receive an answer grounded in real structured data — including a visual chart when the question calls for one. The system translates natural language into safe, validated SQL, executes it against a relational database, and formats the result as both a written answer and, where appropriate, a chart.

The core engineering story is the **agent layer**: intent interpretation, guardrail-validated SQL generation, ambiguity handling, and a provider-agnostic model-switching architecture (Claude, OpenAI, or a locally hosted model via Ollama). Supporting infrastructure is intentionally kept minimal so it doesn't dilute that story.

---

## 2. Problem Statement

Business stakeholders and analysts often need quick answers from structured data but don't write SQL. Existing chatbot demos usually do RAG over documents, not real queries over live relational data — which is a materially different (and harder) problem: correctness, guardrails, and ambiguity handling matter far more than retrieval quality.

---

## 3. Goals (POC scope)

- Accept a natural language question about a dataset.
- Generate and safely execute a read-only SQL query against Postgres.
- Return a natural language answer.
- When the question implies a trend, comparison, or distribution, generate an appropriate chart alongside the text answer.
- Handle ambiguous questions by asking a clarifying follow-up rather than guessing.
- Support switching the underlying LLM (Claude, OpenAI, or a local Ollama model) via config, without changing agent logic.
- Be deployable in a container, with tests covering the guardrail and query-generation logic.

## 3.1 Non-Goals (out of scope for POC)

- Write/mutate operations on the database.
- Multi-turn conversational memory beyond a single clarification round-trip.
- Authentication/authorization, multi-tenancy, or role-based data access.
- Orchestration tooling (Airflow, or any scheduler) — data is loaded via a one-off seed/transform script, not a scheduled pipeline.
- Kubernetes or any cluster deployment — Docker Compose is the full extent of deployment scope.
- User-facing model selection UI — model choice is an env/config setting for this POC, not a chat-UI dropdown.
- Full BI-tool-style dashboarding beyond single-query charts.

---

## 4. User & Use Case

**Primary user:** A non-technical business stakeholder (analyst, PM) who wants to explore a dataset without writing SQL.

**Dataset:** [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (~100k orders, multi-table: orders, order_items, products, customers, sellers, payments, reviews). Chosen because it sits inside the target 100k–1M row range, has real relational structure (forces genuine joins rather than trivial single-table SQL), and is distinctive enough to avoid looking like a copy-paste Northwind/Superstore demo.

**Example interactions:**
- "What were the top 5 products by revenue last quarter?" → text answer + bar chart
- "How has monthly signups trended this year?" → text answer + line chart
- "Show me customers" → clarifying question ("Which attribute — count, list, by region?")

---

## 5. High-Level Architecture

```
┌─────────────┐      ┌──────────────┐      ┌────────────────────┐
│   React     │─────▶│   FastAPI     │─────▶│  Agent Layer         │
│  Frontend   │◀─────│   Backend     │◀─────│  (Pydantic AI)       │
│ (chat + chart)      │  (REST API)  │      └─────────┬───────────┘
└─────────────┘      └──────────────┘                │
                                            ┌───────────▼───────────┐
                                            │  Model Provider        │
                                            │  Abstraction Layer     │
                                            │  (Claude / OpenAI /    │
                                            │   Ollama, env-config)  │
                                            └───────────┬───────────┘
                                                        │
                                            ┌───────────▼───────────┐
                                            │  SQL Generation +      │
                                            │  Guardrail Validator   │
                                            └───────────┬───────────┘
                                                        │
                                            ┌───────────▼───────────┐
                                            │  Postgres (read-only   │
                                            │  role) + dbt models    │
                                            │  (2 models, one-time   │
                                            │  seed/transform)       │
                                            └────────────────────────┘

  Docker Compose: containerized deployment of API + DB for local dev/demo
```

---

## 6. Functional Requirements

### FR1 — Question Intake
System accepts a free-text question via the React chat UI and sends it to the backend API.

### FR2 — Intent & Query Planning
Agent layer (Pydantic AI) interprets the question, determines required tables/columns using a schema description tool, and drafts a SQL query via function calling.

### FR3 — Guardrail Validation
Before execution, generated SQL is validated:
- Must be `SELECT`-only (reject any DDL/DML)
- Must run under a read-only DB role
- Row limit enforced (e.g. max 500 rows)
- Query timeout enforced

### FR4 — Execution & Result Shaping
Validated query executes against Postgres. Results are passed back to the agent to compose a natural language answer.

### FR5 — Chart Decision & Generation
Agent classifies whether the result shape warrants a visualization (e.g. time series → line chart, categorical comparison → bar chart, distribution → histogram, single value → no chart). If so, it returns a structured chart spec (type, x/y fields, data) alongside the text answer.

### FR6 — Chart Rendering (React)
Frontend renders the chart spec using Recharts, alongside the assistant's text answer in the chat thread.

### FR7 — Ambiguity Handling
If the question lacks enough detail to generate a confident query, the agent returns a clarifying question instead of guessing, and the frontend renders it as a normal chat turn awaiting the user's reply.

### FR8 — Model Provider Switching
The agent's underlying LLM is selected via a config/env variable at startup, supporting at minimum: Anthropic Claude API, OpenAI API, and a locally hosted model via Ollama. Swapping providers requires no changes to agent logic — only the provider adapter differs. Not user-facing in this POC (see Non-Goals).

### FR9 — Data Seeding & Transformation
A one-off script loads the Olist dataset into Postgres and runs a small dbt project (2 models: an order-level fact model and a product or customer dimension model) to produce the tables the agent queries against. This is a manual/one-time run for the POC, not a scheduled pipeline.

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Security | DB access via read-only role; no raw query string ever executed without passing validator; secrets via env vars, never hardcoded |
| Testing | TDD with pytest; unit tests for SQL validator, agent tool functions, provider adapter interface, and API endpoints; target meaningful coverage on guardrail logic specifically |
| Reliability | Query timeout + row cap prevent runaway queries; errors surfaced as friendly chat messages, not raw stack traces |
| Observability | Structured logging of each agent call (question → provider used → generated SQL → validation result → execution time); optional lightweight tracing |
| Deployability | Fully containerized via Docker Compose for local dev and demo. No Kubernetes in this POC. |
| Performance | POC target: end-to-end response under ~5s for typical queries against a dataset in the 100k–1M row range, when using a hosted provider (Claude/OpenAI). Local Ollama models are expected to be slower and are not held to this target. |
| Portability | Agent logic must be provider-agnostic: no Claude- or OpenAI-specific assumptions baked into prompts or parsing where avoidable. |

---

## 8. Tech Stack Summary

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript, Recharts for charts |
| Backend API | FastAPI |
| Agent framework | Pydantic AI (function calling, structured output) |
| Database | PostgreSQL |
| Transformation | dbt (2 models — order fact + one dimension) |
| LLM Providers | Anthropic Claude API, OpenAI API, local model via Ollama — switchable via env config |
| Testing | pytest, TDD |
| Deployment | Docker Compose (local dev + demo only) |

---

## 9. Success Criteria for POC

- End-to-end demo: ask a question in the React UI → get correct text answer → get correct chart when applicable.
- At least 3 distinct question types handled correctly (aggregation, trend, comparison).
- At least one ambiguous question correctly triggers a clarification instead of a wrong answer.
- SQL guardrail provably blocks a malicious/destructive query attempt (demonstrable test case).
- Same question, run against at least two different providers (e.g. Claude and Ollama), demonstrably produces correct SQL from both — proving the abstraction actually works, not just that it exists in code.
- Test suite passes in CI; coverage report available.
- Runs via `docker compose up` locally.

---

## 10. Phased Build Plan

**Phase 1 — Core agent loop (highest priority)**
Pydantic AI agent + SQL generation + guardrails + FastAPI + Postgres, tested with pytest, no UI polish. Single provider (Claude) to start.

**Phase 2 — Model provider abstraction**
Add the provider adapter interface; wire up OpenAI and Ollama; add tests proving the same question produces valid SQL across providers.

**Phase 3 — Frontend + charts**
React chat UI, Recharts integration, chart-spec contract between agent and frontend.

**Phase 4 — Data & dbt**
Seed script for the Olist dataset, 2 dbt models.

**Phase 5 — Observability & polish**
Logging/tracing, README with architecture diagram and demo GIF, coverage badge.

---

## 11. Risks & Assumptions

- **Risk:** LLM-generated SQL may hallucinate columns/tables. **Mitigation:** provide schema as a tool/context, validate against actual information_schema before execution.
- **Risk:** Chart-type selection could be wrong for edge cases. **Mitigation:** conservative default (no chart) when uncertain, rather than a misleading chart.
- **Risk:** Local models via Ollama are meaningfully weaker at structured output / function calling than Claude or GPT-class hosted models. Guardrail-validated SQL generation may work noticeably worse on a local model. **Mitigation:** document this as a known, honest limitation in the README rather than hiding it — it's a legitimate finding, not a bug — and don't hold local-model performance to the same success-criteria bar as hosted providers.
- **Assumption:** The Olist Brazilian E-Commerce dataset (public, ~100k orders, multi-table) is sufficient to demonstrate the pattern; no proprietary data needed.

---

## 12. Out of Scope (explicit — for the core POC)

- User authentication
- Multi-tenant data isolation
- Scheduled/orchestrated data pipelines (Airflow or otherwise)
- Kubernetes or any cluster deployment
- User-facing model selection UI
- Full BI-tool-style dashboarding beyond single-query charts

*(Note: the two items above marked "explicit" are picked back up, deliberately, in Section 13 — but only as an optional stretch phase, not as core requirements.)*

---

## 13. Optional Extension — Data Platform (Stretch, Phase 6)

**Status: not required for POC completion.** Build this only if there's a specific reason to — e.g. an application to a role weighted more toward data infrastructure, or spare time after Phases 1–5 are solid. This section exists so the decision to add platform work later is deliberate, not scope creep.

If built, this extension restores and expands the infra that was trimmed out of the core scope, without touching the agent-engineering story:

### 13.1 Airflow
- A real scheduled DAG (not just a doc mention) that re-runs the ingest + dbt transform on a cadence, simulating new orders arriving into the Olist dataset over time (e.g. a synthetic daily batch).
- Single DAG is enough — this is about proving orchestration competence, not building a pipeline suite.

### 13.2 dbt — grown beyond the 2-model core
- Expand from the core's single fact + dimension model into a proper staging → marts layering.
- Add `dbt test` coverage (not_null, relationships, accepted_values) for a real data-quality story — this is a good place to show rigor without much extra time cost.

### 13.3 Kubernetes
- Deployment + Service manifests for the API and Postgres, deployed locally via minikube/kind.
- Explicitly scoped as "demonstrates cluster-deployment familiarity," not production-hardened — no autoscaling, ingress, or secrets-manager integration (consistent with the original v1.1 framing).

### 13.4 Success criteria for this extension (separate from Section 9)
- DAG run is demonstrable end-to-end (trigger → ingest → dbt run → updated tables) with logs to show for it.
- `dbt test` passes and is visible in CI or a demo screenshot.
- `kubectl apply` brings up API + DB locally against the manifests; a query through the running k8s pods works end-to-end.

### 13.5 Risk if built
- **Risk:** Re-introduces the original two-story dilution problem if presented as equally weighted to the agent work. **Mitigation:** always frame this section as "extension" in the README and any resume bullet — lead with the agent story, mention the platform extension as a secondary, clearly-labeled addition.
