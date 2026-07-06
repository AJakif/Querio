# Software Requirements Document (SRD)
## Querio - Natural Language Data Analyst Chatbot (POC)
### *Talk to your data.*

**Version:** 1.4

**Author:** Ahmed Jahin Akif

**Status:** In progress - core POC largely implemented, with selected extension work already landed

**Purpose:** Personal portfolio project targeting Data Software Engineer role

**Changelog (v1.1 -> v1.2):** Re-scoped after a vibe-check pass. Querio became explicitly an agentic AI engineering showcase, not a broad data-platform showcase. Agent framework locked to Pydantic AI. Multi-provider model switching was added. Airflow and Kubernetes were dropped from the core scope.

**Changelog (v1.2 -> v1.3):** Added Section 13 as an optional extension covering Airflow, fuller dbt, and Kubernetes without changing the core POC scope.

**Changelog (v1.3 -> v1.4):** Updated this SRD to match the current repo. Querio now has a working FastAPI + React + Postgres + dbt stack in Docker Compose, multi-provider switching, clarification handling, prompt guardrails, schema-aware SQL repair, dbt tests in the local pipeline, rebuild helper scripts, and a partial Airflow-based refresh extension.

---

## 1. Overview

Querio lets a non-technical user ask a business question in plain English and receive an answer grounded in structured data. The system translates natural language into safe SQL, executes it against Postgres, and returns a natural-language answer plus a chart when appropriate.

The main engineering story is still the agent layer:
- schema-aware SQL generation
- guardrail validation
- ambiguity handling
- provider-agnostic model switching

Supporting infra exists to make the agent story believable, testable, and runnable.

---

## 2. Problem Statement

Business users need quick answers from relational data but often do not write SQL. Most chatbot demos avoid this by doing document retrieval instead. Querio focuses on the harder problem: generating and safely executing SQL over a live relational schema without confidently fabricating nonsense.

---

## 3. Goals (POC scope)

- Accept a natural language question about a dataset.
- Generate and safely execute a read-only SQL query against Postgres.
- Return a natural language answer.
- Generate a chart for trend/comparison-shaped questions when appropriate.
- Handle ambiguous questions by asking clarifying follow-ups.
- Support switching the underlying LLM through config without changing agent logic.
- Be runnable in containers with tests covering core guardrail and query-generation behavior.

## 3.1 Non-Goals (core POC)

- Write/mutate operations on the database.
- Multi-turn conversational memory beyond a single clarification round-trip.
- Authentication, authorization, multi-tenancy, or role-based access controls.
- Kubernetes as part of the core story.
- User-facing provider selection UI.
- Full BI-tool-style dashboarding.
- Arbitrary user-uploaded datasets.

## 3.2 Implementation Snapshot (July 2026)

Implemented now:
- FastAPI `/api/ask` endpoint with answer and clarification response types
- React chat UI with chart rendering
- Pydantic AI SQL generator
- Provider switching across OpenAI, Anthropic, and Ollama
- Schema introspection via `information_schema`
- SQL guardrails for `SELECT`-only behavior plus row-limit injection
- Clarification round-trip support with a conversation store
- Read-only Postgres execution with timeout and schema-aware `search_path`
- One bounded SQL repair retry for retriable schema errors
- Deterministic synthetic raw-data generation
- dbt marts models plus `dbt test` in the local pipeline
- Structured request logging
- Helper scripts for `up`, `down`, `reset`, `rebuild`, `logs`, and `ps`

Partially implemented / still being hardened:
- Strict separation into a dedicated read-only DB role
- Cross-provider proof/demo flow as a polished artifact
- Airflow as a clearly secondary extension
- Coverage/CI/demo collateral as polished portfolio output

Not implemented:
- Kubernetes deployment
- Arbitrary dataset onboarding
- User-facing model selector

---

## 4. User & Use Case

**Primary user:** a non-technical business stakeholder who wants answers without writing SQL.

**Dataset:** Olist Brazilian E-Commerce data shape. The local stack currently uses deterministic synthetic Olist-shaped data as the default demo dataset.

**Representative interactions:**
- "How many orders do we have?"
- "Show total revenue by month."
- "Show me customers."
- "Delete all orders." -> blocked

---

## 5. High-Level Architecture

Frontend (React) -> Backend API (FastAPI) -> Agent layer (Pydantic AI) -> Guardrails + Query execution -> Postgres marts

Supporting components:
- raw synthetic data loader
- dbt transformations from `raw` to `marts`
- Docker Compose local stack
- optional Airflow refresh flow

---

## 6. Functional Requirements

### FR1 - Question Intake
System accepts a free-text question via the React chat UI and sends it to the backend API.
Status: Implemented.

### FR2 - Intent & Query Planning
Agent interprets the question, inspects schema context, and drafts SQL through structured output.
Status: Implemented.

### FR3 - Guardrail Validation
Generated SQL must be validated before execution.
Current runtime guardrails include:
- `SELECT`-only validation
- row-limit injection
- read-only transaction behavior
- timeout enforcement
- prompt-level schema grounding rules
- one schema-aware repair pass for retriable SQL mistakes
Status: Implemented and still being hardened.

### FR4 - Execution & Result Shaping
Validated query executes against Postgres and results are turned into a natural-language answer.
Status: Implemented.

### FR5 - Chart Decision & Generation
System returns a chart spec for supported trend/comparison result shapes.
Status: Implemented for the current line/bar chart flow.

### FR6 - Chart Rendering
Frontend renders the chart spec in the chat thread.
Status: Implemented.

### FR7 - Ambiguity Handling
If the question is vague or unsupported by the schema, the system asks a clarifying question instead of guessing.
Status: Implemented for a single clarification round-trip.

### FR8 - Model Provider Switching
Underlying model is selected via config/env variable.
Status: Implemented.

### FR9 - Data Seeding & Transformation
Local stack seeds data and builds dbt marts before the backend serves queries.
Implementation note: the main happy path currently uses synthetic Olist-shaped data loaded into `raw`, then transformed into `marts`, followed by `dbt test`.
Status: Implemented.

---

## 7. Non-Functional Requirements

| Category | Requirement | Current State |
|---|---|---|
| Security | No unsafe raw SQL should be executed | Implemented through validator + read-only transaction behavior |
| Testing | Pytest coverage on guardrails and core query path | Implemented, still growing |
| Reliability | Friendly failures instead of stack traces in the UI | Implemented |
| Observability | Structured logs across the request path | Implemented |
| Deployability | Fully containerized for local demo | Implemented |
| Performance | Reasonable local demo latency | In progress / model-dependent |
| Portability | Provider-agnostic agent logic | Implemented |

---

## 8. Tech Stack Summary

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript + Recharts |
| Backend API | FastAPI |
| Agent framework | Pydantic AI |
| Database | PostgreSQL |
| Transformation | dbt |
| LLM providers | OpenAI, Anthropic, Ollama |
| Testing | pytest |
| Deployment | Docker Compose |

---

## 9. Success Criteria for POC

- End-to-end demo in the browser
- At least aggregation, trend, and comparison flows work
- At least one ambiguous question triggers clarification
- Destructive query attempts are blocked
- Provider switching works without changing agent logic
- Local stack runs through Docker Compose

### 9.1 Current Status Against Success Criteria

- End-to-end local stack: implemented
- Aggregation / trend / comparison flows: implemented in the current demo path
- Ambiguous question -> clarification flow: implemented
- Destructive query blocking: implemented and tested
- Multi-provider architecture: implemented, though provider quality varies by model
- Docker Compose local run: implemented
- CI / coverage artifacting / polished demo collateral: still in progress

---

## 10. Phased Build Plan Status

### Phase 1 - Core agent loop
Status: Implemented.

### Phase 2 - Model provider abstraction
Status: Implemented at the app-config level; continued hardening is ongoing.

### Phase 3 - Frontend + charts
Status: Implemented for the main POC flow.

### Phase 4 - Data + dbt
Status: Implemented with synthetic raw data, marts models, and dbt tests.

### Phase 5 - Observability + polish
Status: Partially implemented. Logging and README are strong; tracing, artifacts, and portfolio polish are still uneven.

---

## 11. Risks & Assumptions

- **Risk:** LLM-generated SQL hallucinates columns or tables.
  Mitigation: schema tool, stronger prompt guardrails, validator, schema-aware execution, bounded repair retry.
- **Risk:** Local Ollama models perform worse than hosted providers.
  Mitigation: document this honestly and keep provider switching as an architecture proof, not a promise of equal quality.
- **Risk:** Current marts layer does not expose every business grain a demo user might ask for.
  Mitigation: prefer clarification over guessing and keep the demo question set aligned with the current schema.
- **Assumption:** Deterministic synthetic Olist-shaped data is acceptable for the default local demo path.

---

## 12. Out of Scope for the Core POC

- Authentication
- Multi-tenant isolation
- Kubernetes as part of the core deployment story
- Arbitrary dataset ingestion
- User-facing provider selection UI
- Full dashboarding

---

## 13. Optional Extension - Data Platform

This remains a secondary story. It should not overshadow the core agent-engineering narrative.

### 13.1 Airflow
Goal: scheduled refresh of the underlying demo data and dbt models.
Current status: partially implemented in the local extension flow.

### 13.2 dbt growth beyond the minimal marts layer
Goal: expand into a fuller staging -> marts structure with richer tests.
Current status: still a small marts layer, but dbt test coverage has already been added.

### 13.3 Kubernetes
Goal: local cluster deployment to demonstrate cluster familiarity.
Current status: not implemented.

### 13.4 Extension Success Criteria
- refresh flow is demonstrable end to end
- dbt tests pass as part of the extension story
- Kubernetes path works locally if ever built

### 13.5 Presentation Risk
If this extension is presented as equal to the agent story, the portfolio narrative gets diluted. Lead with the agent work; mention platform work as a clearly labeled extension.
