# Querio - User Journey Stories
### Derived from SRD v1.4

Two personas:
- **Stakeholder** - non-technical business user asking questions in the chat UI
- **Operator** - person running, configuring, and demoing the system

Implementation snapshot:
- Most of the core stakeholder journey is now implemented
- Operator setup via Docker Compose is implemented
- Clarification and guardrail journeys are implemented
- Airflow-based refresh exists as an extension
- Kubernetes and arbitrary user-uploaded datasets remain future work

---

## Epic 1 - Asking a Question and Getting an Answer

### 1.1 First question
As a Stakeholder, I want to type a plain-English question into a chat box so that I can explore the data without knowing SQL.

Current state: `Done`

### 1.2 Getting a grounded answer
As a Stakeholder, I want a plain-English answer grounded in the dataset so that I can trust the result.

Current state: `In progress`

Notes:
- Implemented for the core demo path
- Still being hardened around model mistakes and schema repair behavior

### 1.3 Getting a chart when it helps
As a Stakeholder, I want a chart to appear automatically for trend or comparison questions so that I can see the pattern quickly.

Current state: `Done`

Notes:
- Current happy path supports the main line/bar chart flow
- Single-number answers correctly avoid rendering empty charts

### 1.4 Failing safely
As a Stakeholder, I want the system to refuse gracefully instead of crashing or bluffing when my request is unsafe or unsupported.

Current state: `Done`

Notes:
- Guardrail blocks destructive SQL attempts
- Friendly error messaging exists
- Prompt guardrails and bounded repair retry reduce bad-query failures

---

## Epic 2 - Getting Unstuck When My Question Is Vague

### 2.1 Being asked a clarifying question
As a Stakeholder, I want the system to ask what I mean when my question is too vague, so that I do not get a wrong answer presented confidently.

Current state: `Done`

### 2.2 Answering the clarification and getting the real answer
As a Stakeholder, I want my clarification reply to complete my original request, so that I do not have to restate everything from scratch.

Current state: `Done`

Notes:
- Implemented for a single clarification round-trip

---

## Epic 3 - Trusting Where the Data Comes From

### 3.1 Data is coherent for the demo
As a Stakeholder, I want answers to reflect a coherent dataset so that counts, revenue, and dates relate to each other sensibly.

Current state: `In progress`

Notes:
- Synthetic Olist-shaped data plus dbt marts are implemented
- Not every business grain a user might ask for exists in the current marts layer

### 3.2 Bringing my own dataset
As a Stakeholder, I want to upload my own dataset and have Querio understand it automatically.

Current state: `Pending`

Notes:
- Explicitly outside current POC scope
- Would require a separate product/design pass

---

## Epic 4 - Switching the Underlying Model

### 4.1 Running on a hosted provider
As an Operator, I want to run Querio against OpenAI or Anthropic so that I get reliable SQL generation for a polished demo.

Current state: `Done`

### 4.2 Running fully local
As an Operator, I want to run Querio against a local Ollama model so that I can demonstrate provider-agnostic architecture without external APIs.

Current state: `Done`

### 4.3 Proving the abstraction is real
As an Operator, I want to run the same question through multiple providers and show that the abstraction really works.

Current state: `In progress`

Notes:
- The architecture exists
- The polished proof/demo flow still needs to be formalized

---

## Epic 5 - Setting Up and Operating the System

### 5.1 Local setup
As an Operator, I want to bring the whole system up with one command so that reviewers can run it easily.

Current state: `Done`

Notes:
- Docker Compose path is implemented
- Helper scripts now support `reset` and destructive `rebuild`

### 5.2 Seeing what happened under the hood
As an Operator, I want structured logs across the request lifecycle so that I can debug and explain system behavior.

Current state: `Done`

---

## Epic 6 - Data Platform Extension

### 6.1 Refreshing data on a schedule
As an Operator, I want a scheduled refresh path so that I can show the system handling changing data over time.

Current state: `Done`

Notes:
- Airflow-based refresh extension exists in the local stack
- It should still be presented as secondary to the core agent work

### 6.2 Deploying to a cluster
As an Operator, I want to deploy Querio to a local Kubernetes cluster so that I can demonstrate cluster familiarity.

Current state: `Pending`

---

## Summary

What the repo already demonstrates well:
- natural-language question -> SQL -> answer flow
- clarification handling
- prompt + runtime SQL guardrails
- multi-provider architecture
- local full-stack demo environment

What is still a future or polish task:
- stronger provider-proof storytelling
- Kubernetes
- arbitrary dataset onboarding
- final presentation artifacts such as a polished recorded demo
