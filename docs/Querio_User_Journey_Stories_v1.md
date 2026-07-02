# Querio — User Journey Stories
### Derived from SRD v1.3

Two personas:
- **Stakeholder** — the non-technical business user asking questions in the chat UI.
- **Operator** — you, running/deploying/configuring the system (setup, provider switching, deployment).

Stories are written as journeys — read top to bottom within an epic and you're walking through what the user actually experiences, not a task list.

---

## Epic 1 — Asking a Question and Getting an Answer

**1.1 — First question**
> As a Stakeholder, I want to type a plain-English question into a chat box, so that I don't have to know SQL to explore the data.
- **Given** I open Querio for the first time, **when** I type "What were the top 5 products by revenue last quarter?" and hit send, **then** I see my question appear in the chat thread and a loading state while it's processed.

**1.2 — Getting a correct answer**
> As a Stakeholder, I want to receive a plain-English answer grounded in the real dataset, so that I can trust the number without checking it myself.
- **Given** a well-formed question, **when** the system finishes processing, **then** I see a natural-language answer (not raw SQL or a data dump) that correctly reflects the underlying data.

**1.3 — Getting a chart when it helps**
> As a Stakeholder, I want a chart to appear automatically when my question is about a trend or comparison, so that I can see the pattern instead of just reading numbers.
- **Given** I ask "How has monthly signups trended this year?", **when** the answer is returned, **then** I see a line chart alongside the text answer, correctly labeled.
- **Given** I ask a question with a single numeric answer (e.g. "How many orders were placed in total?"), **when** the answer is returned, **then** I see text only — no chart, no empty chart placeholder.

**1.4 — Understanding a wrong or unsafe request without it just failing**
> As a Stakeholder, I want the system to refuse gracefully instead of crashing or returning something misleading, if my question can't be safely answered.
- **Given** the system generates SQL that would be unsafe (e.g. attempts a write, or is malformed), **when** the guardrail blocks it, **then** I see a friendly chat message explaining the question couldn't be answered — not a stack trace, not a wrong answer presented confidently.

---

## Epic 2 — Getting Unstuck When My Question Is Vague

**2.1 — Being asked a clarifying question**
> As a Stakeholder, I want the system to ask me what I mean when my question is too vague, so that I don't get a wrong answer dressed up as a right one.
- **Given** I ask "Show me customers", **when** the system can't confidently determine what I want, **then** I see a clarifying question in the chat thread (e.g. "Which attribute — count, list, or by region?") styled distinctly from a normal answer.

**2.2 — Answering the clarification and getting my real answer**
> As a Stakeholder, I want my reply to the clarifying question to complete my original request, so that I don't have to restate my whole question from scratch.
- **Given** the system just asked me a clarifying question, **when** I reply "by region", **then** the system combines that with my original question and returns a correct, region-broken-down answer — I don't have to retype "show me customers by region" myself.

---

## Epic 3 — Trusting Where the Data Comes From

**3.1 — Data is real and current for the demo**
> As a Stakeholder, I want my answers to reflect a real, coherent dataset, so that the numbers I see actually relate to each other correctly (e.g. revenue matches order counts).
- **Given** the Olist dataset has been seeded and transformed via the 2 dbt models, **when** I ask questions that span orders, products, and customers, **then** the joins resolve correctly and numbers are internally consistent.

**3.2 — (Future, not current scope) Bringing my own dataset**
> As a Stakeholder, I want to upload my own dataset and have the system understand its structure automatically, so that Querio works with my data, not just a demo dataset.
- **Not built in this POC.** Flagged here because it was raised as a north star — see note below on what it would actually take.
- If pulled into scope: would require (a) an upload/connect flow, (b) automatic schema inference against unknown table structures, (c) re-validating the guardrail logic against arbitrary schemas instead of one known schema, (d) handling datasets that don't fit the "clean e-commerce" shape. This is a meaningfully larger project than the current POC — worth scoping as its own epic later, not squeezed into this one.

---

## Epic 4 — Switching the Underlying Model (Operator journey)

**4.1 — Running on a hosted provider**
> As an Operator, I want to run Querio against Claude or OpenAI, so that I get the most reliable SQL generation for a polished demo.
- **Given** `MODEL_PROVIDER=claude` (or `openai`) is set, **when** I start the system, **then** all agent calls route through that provider with no code changes needed.

**4.2 — Running fully local**
> As an Operator, I want to run Querio against a local Ollama model, so that I can demo a provider-agnostic architecture without depending on external APIs.
- **Given** `MODEL_PROVIDER=ollama` is set and a model is pulled locally, **when** I start the system, **then** the agent runs entirely offline — with the understanding (documented in the README) that SQL-generation reliability may be lower than hosted providers.

**4.3 — Proving the abstraction isn't fake**
> As an Operator, I want to run the *same* question through all three providers and see all three succeed, so that I can honestly claim the abstraction works, not just that the code compiles.
- **Given** a fixed test question, **when** I run it against Claude, OpenAI, and Ollama in turn, **then** each produces valid, guardrail-passing SQL — this is my demo proof point, not just an internal test.

---

## Epic 5 — Setting Up and Deploying (Operator journey)

**5.1 — Local setup**
> As an Operator, I want to bring the whole system up with one command, so that anyone reviewing my portfolio can run it without a complicated setup.
- **Given** the repo is cloned, **when** I run `docker compose up`, **then** the API, frontend, and Postgres are all running and the chat UI is reachable in the browser.

**5.2 — Seeing what happened under the hood**
> As an Operator, I want structured logs of each question's journey (question → provider → generated SQL → validation result → execution time), so that I can debug issues and show reviewers the guardrail is really doing work.
- **Given** any question is asked, **when** I check the logs, **then** I can see the full trail for that request in one place.

---

## Epic 6 — Data Platform Extension (Stretch, Operator journey)

**6.1 — Data refreshing on a schedule**
> As an Operator, I want a scheduled job to refresh the underlying data automatically, so that I can demonstrate the system handling data that changes over time, not just a static snapshot.
- **Given** the Airflow DAG is deployed and scheduled, **when** it runs, **then** new synthetic orders are ingested and the dbt models rebuild — visible in logs/run history.

**6.2 — Deploying to a cluster**
> As an Operator, I want to deploy Querio's API and database to a local Kubernetes cluster, so that I can demonstrate cluster-deployment familiarity.
- **Given** the k8s manifests and a running minikube/kind cluster, **when** I `kubectl apply` them, **then** the API and DB come up as pods/services, and a real question through the running cluster returns a correct answer — not just "the pods started."

---

## Note on 3.2

This is the one story that doesn't map to current SRD scope — I wrote it because you described it, but it's marked as future/not-built so it doesn't quietly become an assumed requirement. If you want it pulled into the real backlog, it changes Epic 1's foundation (the schema tool currently assumes one known dataset) enough that it's worth its own scoping pass rather than being folded into Epic 3 as-is.
