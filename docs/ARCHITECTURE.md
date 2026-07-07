# Architecture

## System diagram

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

## Repository structure

```
querio/
├── backend/
│   ├── app/
│   │   ├── main.py                            # FastAPI entrypoint
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── ask.py                     # POST /ask
│   │   │       └── upload.py                  # POST /upload/preview, /upload/confirm
│   │   ├── schemas/
│   │   │   ├── ask.py                         # API request/response DTOs
│   │   │   └── upload.py
│   │   ├── domain/
│   │   │   ├── models.py                      # Question, Answer, ClarifyingQuestion, ChartSpec, SqlQuery
│   │   │   └── exceptions.py                  # GuardrailViolation, AmbiguousQuestion
│   │   ├── repositories/                      # Repository pattern
│   │   │   ├── base.py                        # Abstract interfaces (ABCs)
│   │   │   ├── memory/
│   │   │   │   ├── schema_repository_memory.py
│   │   │   │   └── query_repository_memory.py
│   │   │   └── postgres/
│   │   │       ├── schema_repository_pg.py    # reads information_schema (configurable schema)
│   │   │       └── query_repository_pg.py     # read-only execution
│   │   ├── agent/
│   │   │   ├── agent.py                       # Pydantic AI agent definition
│   │   │   ├── prompts.py
│   │   │   └── tools.py                       # exposes schema_repository as a tool
│   │   ├── guardrails/
│   │   │   └── sql_validator.py               # pure function(s), no DB dependency
│   │   ├── services/
│   │   │   ├── ask_service.py                 # agent + validator + repositories, glued together
│   │   │   ├── csv_ingestion.py               # CSV/JSON parsing + type inference
│   │   │   └── session_manager.py             # upload session lifecycle
│   │   └── core/
│   │       ├── config.py                      # settings/env
│   │       ├── db.py                          # connection/session factory
│   │       └── logging.py
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── scripts/
│   │   ├── load_raw.py                        # generates Olist data into raw schema
│   │   └── download_olist.py                  # downloads real Olist CSVs from Kaggle
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatThread.tsx
│   │   │   ├── ChatBubble.tsx
│   │   │   ├── UploadZone.tsx
│   │   │   ├── SchemaPreview.tsx
│   │   │   └── charts/
│   │   │       └── ChartWidget.tsx
│   │   ├── api/
│   │   │   ├── askApi.ts
│   │   │   └── uploadApi.ts
│   │   ├── types/api.ts
│   │   └── App.tsx
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
│
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── sources.yml
│       └── marts/
│           ├── schema.yml
│           ├── fct_orders.sql
│           └── dim_customers.sql
│
├── docker-compose.yml
├── .env.example
├── Images/
│   └── mock_1.jpg
├── README.md
└── docs/
    ├── ARCHITECTURE.md
    ├── SETUP.md
    ├── DATASET.md
    ├── DEMO_QUESTIONS.md
    ├── POC_SRD_NL_Data_Chatbot_v1.3.md
    └── Querio_User_Journey_Stories_v1.md
```
