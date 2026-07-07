# Querio

### Talk to your data.

Ask a business question in plain English, get a grounded answer pulled from a real Postgres database — with a chart when one actually helps — instead of a wall of SQL you'd have to write yourself.

Built to demonstrate agentic AI engineering: guardrail-validated SQL generation, ambiguity handling, and a provider-agnostic model architecture that runs against Claude, OpenAI, or a fully local model.

<img src="./Images/mock_1.jpg" alt="Querio Blueprint workbench — calm chat shell alongside the technical workbench pane with reasoning trace, SQL, and chart" style="width: 100%; max-width: 900px; border-radius: 12px; margin: 24px 0; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">

---

## Quick start

```bash
git clone <repo-url>
cd querio
cp .env.example .env
cp .env.secrets.example .env.secrets
docker compose up
```

Then open `http://localhost:3000` and start asking questions.

Detailed setup, model configuration, and helper scripts → [`docs/SETUP.md`](./docs/SETUP.md)

---

## What it does

- Ask a question like *"What were the top 5 products by revenue last quarter?"* → get a text answer **and** a bar chart.
- Ask something trend-shaped like *"How has monthly signups trended this year?"* → get a line chart.
- Ask something vague like *"Show me customers"* → get asked a clarifying question instead of a wrong answer.
- Every generated query passes through a guardrail validator — `SELECT`-only, row cap, timeout.
- Swap the underlying LLM (Claude / OpenAI / local via Ollama) with a single config change.

---

## Why this project exists

Most "AI chatbot" portfolio demos do RAG over documents. Querio does something harder: it generates and safely executes real SQL against a live relational database. That means correctness, guardrails, and ambiguity handling matter far more than retrieval quality.

---

## Project docs

| Document | What it covers |
|---|---|
| [`ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | System architecture, tech stack, repo tree |
| [`SETUP.md`](./docs/SETUP.md) | Full setup guide, env config, logging, troubleshooting |
| [`DATASET.md`](./docs/DATASET.md) | Olist dataset, raw/marts schemas, data pipeline, Airflow refresh |
| [`DEMO_QUESTIONS.md`](./docs/DEMO_QUESTIONS.md) | Organized demo questions by category |
| [`POC_SRD_NL_Data_Chatbot_v1.3.md`](./docs/POC_SRD_NL_Data_Chatbot_v1.3.md) | Full requirements and architecture decisions |
| [`Querio_User_Journey_Stories_v1.md`](./docs/Querio_User_Journey_Stories_v1.md) | Persona-based stories with acceptance criteria |

---

## Running tests

```bash
pytest --cov
```

Coverage focuses on the guardrail validator, agent tool functions, and the provider adapter interface.

---

## Known limitations

- **Local models are weaker at structured output.** Ollama-hosted models are meaningfully less reliable at function calling / structured SQL generation than Claude or GPT-class models.
- **No auth, no multi-tenancy.** Single-user POC by design.
- **No write operations.** Querio is read-only, on purpose.
- **Model selection is config-only**, not a UI dropdown.

---

## License

TBD.
