# Querio — Epic & Story Backlog
### Derived from SRD v1.3

Each epic maps to a build phase. Stories are sized to be completable in one sitting (a few hours, not days). Size tags: **S** (~1-2 hrs), **M** (~half day), **L** (~1 day).

---

## Epic 1 — Guardrail-Validated SQL Generation (Core Agent Loop)
*Maps to SRD Phase 1. This is the heart of the project — get this rock-solid before anything else.*

- **1.1 (S)** Set up FastAPI skeleton with a single `/ask` POST endpoint that echoes the input back — proves the wiring before any agent logic exists.
- **1.2 (M)** Stand up Postgres locally (Docker Compose) with a read-only DB role, separate from the seed/admin role.
- **1.3 (M)** Write a schema-introspection tool (queries `information_schema`) that the agent can call to see real tables/columns — this is what prevents hallucinated columns later.
- **1.4 (L)** Build the Pydantic AI agent: takes a question + schema tool, produces a structured SQL draft via function calling.
- **1.5 (M)** Build the guardrail validator as a standalone, independently testable module: `SELECT`-only check, row-limit injection, timeout wrapper. *(Testable in isolation before it's wired to the agent — do this first.)*
- **1.6 (S)** Write the "malicious query" test case (e.g. agent asked to do something destructive) and prove the validator blocks it. This is a named success criterion — don't skip it.
- **1.7 (M)** Wire validator → query execution → result passed back to agent for natural-language answer composition.
- **1.8 (M)** Implement FR7: ambiguity detection — agent returns a clarifying question instead of a query when confidence is low, and the API round-trips that as a normal chat turn.
- **1.9 (S)** Pytest suite for: validator (unit), schema tool (unit), one integration test hitting a real (test) Postgres.

**Epic done when:** you can `curl` the `/ask` endpoint with 3 different question types and 1 ambiguous question, and get correct behavior for all 4, with a passing test suite.

---

## Epic 2 — Model Provider Abstraction
*Maps to SRD Phase 2. Don't start until Epic 1 works end-to-end on one provider — abstracting too early makes debugging harder.*

- **2.1 (M)** Define the provider adapter interface (the contract every provider must satisfy — prompt in, structured SQL draft out).
- **2.2 (S)** Confirm the Claude adapter (already built in Epic 1) conforms cleanly to that interface — refactor if it snuck in assumptions.
- **2.3 (M)** Build the OpenAI adapter against the same interface.
- **2.4 (M)** Build the Ollama adapter — flag early if a given local model can't do structured output reliably; this is expected, not a bug (see SRD Risk in §11).
- **2.5 (S)** Env-config switch (`MODEL_PROVIDER=claude|openai|ollama`) that swaps providers with zero agent-logic changes.
- **2.6 (M)** Test: run the *same* fixed question through all 3 providers, assert all 3 produce valid (guardrail-passing) SQL. This is your named success criterion from SRD §9 — the actual proof the abstraction isn't fake.

**Epic done when:** flipping the env var is the only thing that changes between provider runs, and you have a test proving it.

---

## Epic 3 — Chat Frontend + Chart Rendering
*Maps to SRD Phase 3.*

- **3.1 (M)** React + TypeScript scaffold, basic chat thread UI (message list + input box), no styling polish yet.
- **3.2 (S)** Wire chat UI to the `/ask` endpoint — send question, render text answer as a chat bubble.
- **3.3 (M)** Define the chart-spec contract (type, x/y fields, data) as a shared TypeScript type mirroring the Pydantic model from Epic 1.4.
- **3.4 (M)** Recharts integration: render bar chart from spec.
- **3.5 (S)** Recharts: line chart from spec.
- **3.6 (S)** Recharts: histogram/distribution chart from spec.
- **3.7 (S)** Handle the "no chart" case gracefully (single-value answers) — text only, no empty chart placeholder.
- **3.8 (M)** Render clarifying questions (FR7) as a distinct chat-turn style so it's visually clear the agent is asking, not answering.
- **3.9 (S)** Basic loading/error states — friendly message on backend failure, not a raw stack trace (ties to SRD Reliability NFR).

**Epic done when:** all 3 required question types (aggregation, trend, comparison) render correctly end-to-end in the browser, plus the ambiguous-question flow.

---

## Epic 4 — Data Seeding & dbt Transformation
*Maps to SRD Phase 4. Can actually be done in parallel with Epic 1 by someone else — or by you, early, so Epic 1 has real data to query against sooner.*

- **4.1 (S)** Download Olist dataset, write a one-off script to load raw CSVs into a `raw` schema in Postgres.
- **4.2 (M)** dbt project setup, connected to the Postgres instance.
- **4.3 (M)** dbt model 1: order-level fact table (joins orders + order_items + payments).
- **4.4 (M)** dbt model 2: a dimension model (customers or products — pick whichever makes your 3 demo questions cleanest).
- **4.5 (S)** Point the agent's schema-introspection tool (1.3) at the dbt output tables, not raw tables.

**Epic done when:** `dbt run` produces the 2 models, and Epic 1's agent is querying against them successfully.

---

## Epic 5 — Observability, Testing & Polish
*Maps to SRD Phase 5. This is what makes the demo look finished, not just functional.*

- **5.1 (S)** Structured logging: question → provider used → generated SQL → validation result → execution time, one log line per request.
- **5.2 (S)** (Optional) lightweight tracing if time allows — skip without guilt if short on time.
- **5.3 (M)** Coverage report wired into pytest run; badge generation.
- **5.4 (M)** CI pipeline (GitHub Actions) running the test suite on push.
- **5.5 (L)** README: architecture diagram (reuse SRD §5), setup instructions, and the honest note about local-model limitations (SRD §11 risk) — this kind of candor reads well to engineers reviewing the repo.
- **5.6 (M)** Record the demo GIF: 3 question types + 1 ambiguous question + the multi-provider proof from 2.6.

**Epic done when:** a stranger can clone the repo, follow the README, run `docker compose up`, and reproduce your demo GIF.

---

## Epic 6 — Data Platform Extension (Stretch, Optional)
*Maps to SRD §13. Only start this after Epics 1–5 are genuinely done. Do not let this epic bleed into the "core" story — see SRD §13.5 risk.*

- **6.1 (M)** Airflow: single DAG that re-runs the 4.1 ingest + dbt transform on a schedule.
- **6.2 (S)** Synthetic "new orders" generator so the DAG has something to actually process on each run (otherwise the demo is a no-op).
- **6.3 (M)** Expand dbt from 2 models into staging → marts layering.
- **6.4 (M)** Add `dbt test` coverage (not_null, relationships, accepted_values) on the new layer.
- **6.5 (L)** Kubernetes manifests: Deployment + Service for API and Postgres.
- **6.6 (M)** Validate end-to-end against a local minikube/kind cluster — a query actually working through the running pods, not just `kubectl apply` succeeding silently.
- **6.7 (S)** README addendum clearly labeled "optional extension" — keep this visually and narratively separate from the core project description.

**Epic done when:** the platform extension is fully functional but still reads as a clearly-labeled secondary addition, not the headline of the project.

---

## Suggested build order

1. Epic 1 (core agent loop) — with Epic 4 running in parallel if you can, so real data exists sooner.
2. Epic 2 (provider abstraction) — only once Epic 1 is solid on one provider.
3. Epic 3 (frontend) — can start once Epic 1's `/ask` contract is stable, doesn't need to wait for Epic 2.
4. Epic 5 (polish) — continuous in small pieces, not one big push at the end.
5. Epic 6 (stretch) — only if there's a specific reason to, per SRD §13.
