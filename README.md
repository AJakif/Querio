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
                                             │  Postgres — marts      │
                                             │  schema (fct_orders,   │
                                             │  dim_customers)        │
                                             └───────────┬───────────┘
                                                         │
                                             ┌───────────▼───────────┐
                                             │  dbt transforms        │
                                             │  raw → marts           │
                                             └───────────┬───────────┘
                                                         │
                                             ┌───────────▼───────────┐
                                             │  raw schema            │
                                             │  (9 Olist tables,      │
                                             │   loaded by seed)      │
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
│   │   │   ├── memory/
│   │   │   │   ├── schema_repository_memory.py
│   │   │   │   └── query_repository_memory.py
│   │   │   └── postgres/
│   │   │       ├── schema_repository_pg.py    # reads information_schema (configurable schema)
│   │   │       └── query_repository_pg.py     # read-only execution
│   │   │
│   │   ├── providers/                         # LLM provider abstraction (stub)
│   │   │   └── __init__.py
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
│   │   │   └── ... (only .pyc remnants)
│   │   └── conftest.py
│   │
│   ├── scripts/
│   │   ├── load_raw.py                        # generates Olist data into raw schema
│   │   ├── download_olist.py                  # downloads real Olist CSVs from Kaggle
│   │   └── seed.py                            # (legacy) seeds public schema directly
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
│   │   │       └── ChartWidget.tsx
│   │   ├── api/askApi.ts
│   │   ├── types/api.ts
│   │   └── App.tsx
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf                              # used by Dockerfile's runtime stage
│   └── .dockerignore
│
├── dbt/
│   ├── dbt_project.yml                        # dbt project config → marts schema
│   ├── profiles.yml                            # Postgres connection profile
│   └── models/
│       ├── sources.yml                         # raw schema source definitions
│       └── marts/
│           ├── schema.yml                      # model docs + column-level tests
│           ├── fct_orders.sql                   # order-level fact table
│           └── dim_customers.sql                # customer dimension
│
├── docker-compose.yml                          # full stack: postgres + seed + dbt + api + frontend
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
| Transformation | dbt (2 models: `fct_orders`, `dim_customers`) |
| LLM providers | Anthropic Claude, OpenAI, local via Ollama — switchable via env config |
| Testing | pytest, TDD |
| Deployment | Docker Compose |

---

## Dataset

[Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — ~100k orders across orders, order items, products, customers, sellers, payments, and reviews. Chosen because it has real relational structure (the agent has to reason across joins, not just filter one flat table) and sits comfortably in the 100k–1M row performance target.

The project works with deterministic synthetic data that mirrors the Olist schema exactly. The download script (`scripts/download_olist.py`) is available if you want the real CSVs.

---

## Getting started

```bash
git clone <repo-url>
cd querio
cp .env.example .env
cp .env.secrets.example .env.secrets
docker compose up
```

Then open `http://localhost:3000` (or whatever port the frontend maps to) and start asking questions.

If you want a shorter local command on Windows/PowerShell, use:

```powershell
.\scripts\querio.ps1 up
```

On Linux/macOS, use:

```bash
./scripts/querio.sh up
```

To stop the stack:

```bash
docker compose down
```

Or:

```powershell
.\scripts\querio.ps1 down
```

```bash
./scripts/querio.sh down
```

To fully reset Postgres data and trigger a clean re-seed on the next startup:

```bash
docker compose down --volumes
```

PowerShell helper extras:

```powershell
.\scripts\querio.ps1 up -Detached
.\scripts\querio.ps1 logs
.\scripts\querio.ps1 ps
.\scripts\querio.ps1 reset
```

Unix helper extras:

```bash
./scripts/querio.sh up -d
./scripts/querio.sh logs
./scripts/querio.sh ps
./scripts/querio.sh reset
```

### Data pipeline

`docker compose up` runs the full pipeline automatically:

1. **Postgres** starts and waits for health.
2. **Seed** (`python scripts/load_raw.py`) creates the `raw` schema and populates 9 tables with deterministic Olist-like data.
3. **dbt** runs `dbt run`, which transforms `raw` → `marts` schema producing two analytical models:
   - `fct_orders` — order-level fact table (orders + items + payments)
   - `dim_customers` — customer dimension with aggregated order metrics
4. **Airflow** starts at `http://localhost:8081` and loads the `scheduled_data_refresh` DAG so refresh runs and run history are visible in the UI.
5. **Backend** starts, configured to read schema from the `marts` schema (`DB_SCHEMA=marts`).
6. **Frontend** starts, serving the chat UI.

The agent queries the clean `marts` schema tables — not the raw normalized tables — so joins are simpler and query generation is more reliable.

### Configuring the model

Querio's LLM is chosen entirely via config — no code changes needed to switch:

```bash
# .env
APP_ENV=dev
DATABASE_URL=postgresql://querio:querio@localhost:5432/querio
DB_SCHEMA=marts
MODEL_PROVIDER=openai
MODEL_NAME=openai:gpt-4o-mini
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434/v1
LOG_LEVEL=
QUERIO_SECRETS_FILE=.env.secrets
```

```bash
# .env.secrets
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

Examples:

- `MODEL_PROVIDER=openai` and `MODEL_NAME=gpt-4o-mini` with `OPENAI_API_KEY=...`
- `MODEL_PROVIDER=claude` and `MODEL_NAME=claude-3-5-sonnet-latest` with `ANTHROPIC_API_KEY=...`
- `MODEL_PROVIDER=ollama` and `OLLAMA_MODEL=llama3.1` with Ollama running at `OLLAMA_BASE_URL`

The backend loads secrets in this order:

- direct env vars like `OPENAI_API_KEY`
- file paths like `OPENAI_API_KEY_FILE`
- the dotenv-style file pointed to by `QUERIO_SECRETS_FILE`

The default Docker setup mounts `./.env.secrets` read-only into the container and reads `/run/secrets/querio.env`, so provider keys do not need to appear in `docker-compose.yml` or your main `.env`.

If hosted provider API keys are blank, Querio falls back to its built-in fake SQL generator so the local stack can still boot for wiring checks. Real natural-language SQL generation requires a valid hosted provider API key or a reachable local Ollama server.

### Logging

The backend logger is environment-aware:

- `APP_ENV=dev` uses a human-readable console format and defaults to `DEBUG`
- `APP_ENV=prod` uses structured JSON logs and defaults to `INFO`
- logs are also written to `backend/logs/querio.log`
- `LOG_LEVEL` can override either default when you need a specific level

---

## Data pipeline

The project uses a two-layer data architecture:

```
raw (seed script)  ──▶  dbt run  ──▶  marts (agent queries this layer)
```

- **`raw` schema** (9 tables): mirrors the original Olist CSV structure. Populated by `python scripts/load_raw.py` with deterministic, arithmetically coherent sample data (~9,500 rows).
- **`marts` schema** (2 models): analytical tables produced by dbt. The agent introspects this schema to generate queries.

### Raw schema tables

| Table | Rows | Description |
|---|---|---|
| `raw.customers` | 1,000 | Brazilian e-commerce customers with state/city |
| `raw.orders` | 5,000 | Orders with status, timestamps |
| `raw.order_items` | ~5,500 | Line items per order |
| `raw.order_payments` | 5,000 | Payment method/installments |
| `raw.order_reviews` | ~4,775 | Review scores and comments |
| `raw.products` | 60 | Products across 30 categories |
| `raw.sellers` | 50 | Sellers across Brazilian states |
| `raw.geolocation` | ~200 | Zip-code-level lat/lng data |
| `raw.product_category_name_translation` | 30 | Portuguese-to-English category name translation |

### Marts models (dbt output)

| Model | Type | Description |
|---|---|---|
| `marts.fct_orders` | Fact table | Order-level: joins orders + items + payments. One row per order with aggregated item/payment metrics. |
| `marts.dim_customers` | Dimension | Customer details with lifetime order aggregates (total orders, total spent, avg order value, first/last order date). |

### Re-seeding and rebuilding

```bash
# Full reset: reload raw data and rebuild dbt models
python scripts/load_raw.py
cd dbt && dbt run
```

The seed script uses a fixed random seed (`SEED = 42`), so every run produces identical results. This guarantees reproducible data for development, testing, and demo purposes.

### Scheduled refresh with Airflow

The `scheduled_data_refresh` DAG runs hourly and uses `python scripts/append_synthetic_orders.py` to append new synthetic orders into the raw schema instead of replaying the same seed from scratch. It then runs `dbt run` so the `marts` schema reflects the added rows.

- Open `http://localhost:8081` to inspect the Airflow UI.
- Trigger `scheduled_data_refresh` manually or wait for the next schedule.
- Confirm run history and task logs in Airflow after each refresh.
- Ask a freshness-sensitive question after the run to verify the rebuilt marts tables reflect the new orders.

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
