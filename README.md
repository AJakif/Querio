# Querio

### Talk to your data.

Querio is a natural-language data analyst chatbot. Ask a business question in plain English, get a grounded answer pulled from a real Postgres database — with a chart when one actually helps — instead of a wall of SQL you'd have to write yourself.

This is a portfolio project built to demonstrate agentic AI engineering: guardrail-validated SQL generation, ambiguity handling, and a provider-agnostic model architecture that runs against Claude, OpenAI, or a fully local model — not just "I called an LLM API."

**Status:** In development (POC scope) · See [`POC_SRD_NL_Data_Chatbot_v1.3.md`](./docs/POC_SRD_NL_Data_Chatbot_v1.3.md) for the full requirements doc.

---

## Why this project exists

Most "AI chatbot" portfolio demos do RAG over documents. Querio does something harder: it generates and safely executes real SQL against a live relational database. That means correctness, guardrails, and ambiguity handling matter far more than retrieval quality — and that's the actual engineering problem this project is built to show off.

---

## What it does

- Ask a question like *"What were the top 5 products by revenue last quarter?"* → get a text answer **and** a bar chart.
- Ask something trend-shaped like *"How has monthly signups trended this year?"* → get a line chart.
- Ask something vague like *"Show me customers"* → get asked a clarifying question instead of a wrong answer.
- Every generated query passes through a guardrail validator before it ever touches the database — `SELECT`-only, read-only DB role, row limit, query timeout.
- Swap the underlying LLM (Claude / OpenAI / local via Ollama) with a single config change — no agent code changes required.

---

## Architecture

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
                                            └────────────────────────┘
```

The agent never talks to the database directly. Every generated query is checked against a validator (`SELECT`-only, row cap, timeout) and runs under a read-only DB role — there's no code path where a raw, unvalidated query string reaches Postgres.

```
querio/
├── backend/
│   ├── app/
│   │   ├── main.py                            # FastAPI entrypoint
│   │   │
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── ask.py                     # POST /ask
│   │   │
│   │   ├── schemas/                           # API request/response DTOs
│   │   │   └── ask.py
│   │   │
│   │   ├── domain/                            # framework-agnostic core models
│   │   │   ├── models.py                      # Question, Answer, ClarifyingQuestion, ChartSpec, SqlQuery
│   │   │   └── exceptions.py                  # GuardrailViolation, AmbiguousQuestion
│   │   │
│   │   ├── repositories/                      # ★ repository pattern ★
│   │   │   ├── base.py                        # abstract interfaces (ABCs)
│   │   │   ├── schema_repository.py           # SchemaRepository(ABC): get_tables(), get_columns()
│   │   │   ├── query_repository.py            # QueryRepository(ABC): execute(sql) -> rows
│   │   │   └── postgres/
│   │   │       ├── schema_repository_pg.py    # concrete: reads information_schema
│   │   │       └── query_repository_pg.py     # concrete: runs under read-only role
│   │   │
│   │   ├── providers/                         # LLM provider abstraction (same pattern)
│   │   │   ├── base.py                        # ModelProvider(ABC)
│   │   │   ├── claude_provider.py
│   │   │   ├── openai_provider.py
│   │   │   ├── ollama_provider.py
│   │   │   └── factory.py                     # env-config → concrete provider
│   │   │
│   │   ├── agent/
│   │   │   ├── agent.py                       # Pydantic AI agent definition
│   │   │   ├── prompts.py
│   │   │   └── tools.py                       # exposes schema_repository as a tool
│   │   │
│   │   ├── guardrails/
│   │   │   └── sql_validator.py                # pure function(s), no DB dependency
│   │   │
│   │   ├── services/                          # orchestration layer
│   │   │   └── ask_service.py                  # agent + validator + repositories, glued together
│   │   │
│   │   └── core/
│   │       ├── config.py                       # settings/env
│   │       ├── db.py                           # connection/session factory
│   │       └── logging.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_sql_validator.py
│   │   │   ├── test_providers.py
│   │   │   └── test_ask_service.py             # uses FAKE repositories, no real DB needed
│   │   ├── integration/
│   │   │   └── test_ask_endpoint.py            # real Postgres, real repositories
│   │   ├── fakes/
│   │   │   ├── fake_schema_repository.py
│   │   │   └── fake_query_repository.py
│   │   └── conftest.py
│   │
│   ├── scripts/
│   │   └── seed.py                             # loads Olist CSVs into raw schema
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatThread.tsx
│   │   │   ├── ChatBubble.tsx
│   │   │   └── charts/
│   │   │       ├── BarChart.tsx
│   │   │       ├── LineChart.tsx
│   │   │       └── Histogram.tsx
│   │   ├── api/askApi.ts
│   │   ├── types/chartSpec.ts
│   │   └── App.tsx
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf                              # used by Dockerfile's runtime stage
│   └── .dockerignore
│
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   └── marts/
│   └── dbt_project.yml
│
├── docker-compose.yml                          # not yet written
├── .env.example
├── README.md
└── docs/
    ├── POC_SRD_NL_Data_Chatbot_v1.3.md
    ├── Querio_Epics_Backlog_v1.md
    └── Querio_User_Journey_Stories_v1.md

```

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript, Recharts |
| Backend API | FastAPI |
| Agent framework | Pydantic AI |
| Database | PostgreSQL |
| Transformation | dbt (2 models) |
| LLM providers | Anthropic Claude, OpenAI, local via Ollama — switchable via env config |
| Testing | pytest, TDD |
| Deployment | Docker Compose |

---

## Dataset

[Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — ~100k orders across orders, order items, products, customers, sellers, payments, and reviews. Chosen because it has real relational structure (the agent has to reason across joins, not just filter one flat table) and sits comfortably in the 100k–1M row performance target.

---

## Getting started

```bash
git clone <repo-url>
cd querio
cp .env.example .env   # set your provider + API key(s), see below
docker compose up
```

Then open `http://localhost:3000` (or whatever port the frontend maps to) and start asking questions.

### Configuring the model provider

Querio's LLM is chosen entirely via env config — no code changes needed to switch:

```bash
# .env
MODEL_PROVIDER=claude   # or: openai | ollama
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...      # only needed if MODEL_PROVIDER=openai
OLLAMA_MODEL=llama3     # only needed if MODEL_PROVIDER=ollama, model must be pulled locally
```

If you're running against Ollama, make sure the model is pulled first: `ollama pull llama3`.

---

## Seeding the data

The seed script creates the full Olist Brazilian E-Commerce dataset schema (9 tables with foreign key relationships) and populates it with deterministic, reproducible sample data (~9,500 rows). The data is arithmetically coherent: payment values match item totals, dates are internally consistent, and foreign keys resolve correctly across all entities.

```bash
# one-off: create the schema and seed with deterministic Olist data
python scripts/seed.py
```

The script uses a fixed random seed (`SEED = 42`), so every run produces identical results. This guarantees reproducible data for development, testing, and demo purposes.

### Schema overview

| Table | Rows | Description |
|---|---|---|
| `customers` | 1,000 | Brazilian e-commerce customers with state/city |
| `orders` | 5,000 | Orders with status, timestamps, FKs to customers |
| `order_items` | ~5,500 | Line items per order, FKs to products & sellers |
| `order_payments` | 5,000 | Payment method/installments per order |
| `order_reviews` | ~4,775 | Review scores and comments for delivered orders |
| `products` | 60 | Products across 30 categories with physical specs |
| `sellers` | 50 | Sellers across Brazilian states |
| `geolocation` | ~200 | Zip-code-level lat/lng data |
| `product_categories` | 30 | Portuguese-to-English category name translation |

### Foreign key relationships

```
orders.customer_id      -> customers.customer_id
order_items.order_id    -> orders.order_id
order_items.product_id  -> products.product_id
order_items.seller_id   -> sellers.seller_id
order_payments.order_id -> orders.order_id
order_reviews.order_id  -> orders.order_id
```

### Arithmetic coherence

The generated data is internally consistent:
- `order_payments.payment_value` equals the sum of `order_items.price + freight_value` for each order
- Order timestamps follow a strict sequence: purchase → approval → carrier → delivery
- Only `delivered` orders have populated delivery dates
- Review scores have a realistic distribution (skewed positive, ~70% at 4+)

### Re-seeding

To reset the database and re-seed (e.g., after schema changes or to get a fresh copy):

```bash
python scripts/seed.py
```

The script drops all existing tables and recreates them from scratch. Since the seed is deterministic, the same data is produced every time.

This is a manual, one-time step for the POC — not a scheduled pipeline (see [Known limitations](#known-limitations) and the optional extension below).

---

## Running tests

```bash
pytest --cov
```

Coverage focuses on the guardrail validator, agent tool functions, and the provider adapter interface. There's a specific test proving the guardrail blocks a malicious/destructive query attempt, and a test proving the same question produces valid SQL across all three providers — that's the actual proof the provider abstraction works, not just that the code compiles.

---

## Known limitations

- **Local models are weaker at structured output.** Ollama-hosted models are meaningfully less reliable at function calling / structured SQL generation than Claude or GPT-class models. This is documented honestly rather than hidden — it's a real finding about provider tradeoffs, not a bug.
- **No auth, no multi-tenancy.** Single-user POC by design.
- **No write operations.** Querio is read-only, on purpose — see the guardrail validator.
- **Model selection is config-only in this POC**, not a UI dropdown.

---

## Optional extension: data platform

There's a scoped-out "Phase 6" extension (Airflow scheduling, a fuller dbt staging→marts layer, Kubernetes manifests) documented in the SRD under **Section 13**. It's intentionally kept separate from the core project so the headline story stays "agent engineering," not "I also configured Airflow once." Only relevant if you're digging into infra depth specifically.

---

## Project docs

- [SRD v1.3](./docs/POC_SRD_NL_Data_Chatbot_v1.3.md) — full requirements, architecture, and scope decisions
- [Epic & Story Backlog](./docs/Querio_Epics_Backlog_v1.md) — build-order task breakdown
- [User Journey Stories](./docs/Querio_User_Journey_Stories_v1.md) — persona-based stories with acceptance criteria

---

## License

TBD.