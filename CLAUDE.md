# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Querio — a natural-language-to-SQL chat app. The agent turns a plain-English question into a guardrail-validated, read-only SQL query against a Postgres `marts` schema (dbt-transformed from whatever is loaded into `raw`), executes it, and returns an answer plus an optional chart. Users upload their own CSV/JSON in-chat to query against a session-scoped schema; the base `raw`/`marts` schema ships empty (no bundled demo dataset) and is populated only if you load your own data into it directly.

## Commands

### Full stack (Docker Compose)

```bash
cp .env.example .env
cp .env.secrets.example .env.secrets
docker compose up               # starts postgres -> seed -> dbt -> airflow -> backend -> frontend
```

Helper scripts wrap Compose (`up`, `up -Detached`/`-d`, `down`, `logs`, `ps`, `reset`, `rebuild`):

```powershell
.\scripts\querio.ps1 up
```
```bash
./scripts/querio.sh up
```

`reset` clears data; `rebuild` is destructive (removes containers/volumes/images, then rebuilds). Data reset: `docker compose down --volumes`.

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Airflow: http://localhost:8081

### Backend (FastAPI + Pydantic AI), from `backend/`

```bash
pytest --cov                          # all tests
pytest tests/unit                     # unit only
pytest tests/integration              # integration only (some need a live Postgres)
pytest tests/unit/test_sql_validator.py::test_name   # single test
uvicorn app.main:app --reload         # run API locally (needs DATABASE_URL etc. in env)
```

No lint/format tooling is configured in this repo (no ruff/black/mypy config) — don't assume one exists.

### Frontend (React + TS + Vite), from `frontend/`

```bash
npm run dev          # dev server
npm run build         # tsc -b && vite build
npm run test          # vitest run (single run)
npm run test:watch    # vitest watch
```

### dbt, from `dbt/`

```bash
dbt run    # raw -> marts
dbt test
```

## Architecture

```
React (chat + upload + chart) -> FastAPI (REST) -> Pydantic AI agent -> guardrail validator -> Postgres (marts schema)
```

Data flow: `raw` schema (9 tables matching the Olist Brazilian E-Commerce structure, created empty by `backend/scripts/load_raw.py`) -> dbt transforms -> `marts` schema (`fct_orders`, `dim_customers`) is what the agent actually queries. Airflow runs a scheduled refresh DAG (`backend/app/orchestration/scheduled_data_refresh_dag.py`, mounted into `infra/airflow/dags`) that re-runs `dbt run`/`dbt test` over whatever is currently in `raw`.

**The agent never talks to Postgres directly.** Every LLM-generated query passes through `app/guardrails/sql_validator.py` (SELECT-only, row cap, timeout) before being handed to a query repository. Keep that boundary — don't let generated SQL bypass the validator on any new code path.

### Backend layering (`backend/app/`)

- `api/routes/` — FastAPI routers: `ask.py` (POST `/ask`), `upload.py` (CSV/JSON upload preview+confirm), `session.py` (upload session lifecycle).
- `schemas/` — request/response DTOs (pydantic), separate from...
- `domain/models.py` — internal domain types (`Question`, `Answer`, `ClarifyingQuestion`, `ChartSpec`, `SqlQuery`) and `domain/exceptions.py` (`GuardrailViolation`, `AmbiguousQuestion`).
- `agent/` — Pydantic AI agent (`agent.py`), system prompt (`prompts.py`), tool exposing the schema repository to the LLM (`tools.py`). `agent.py` builds the model adapter (`AnthropicModel`/`OpenAIChatModel`, Ollama via the OpenAI-compatible provider) from `model_name` string like `"openai:gpt-4o-mini"`; falls back to `FakeSqlGenerator` when no provider API key is configured, so the stack still boots without secrets.
- `repositories/` — repository pattern with an ABC layer in `base.py`, both an `memory/` (in-memory, used in tests) and `postgres/` implementation for schema introspection and read-only query execution.
- `guardrails/sql_validator.py` — pure functions, no DB dependency. This is the single security boundary for generated SQL.
- `services/` — glue layer: `ask_service.py` (agent + validator + repos), `csv_ingestion.py` (upload parsing + type inference), `session_manager.py` / `conversation_store.py` (upload/session state), `data_refresh.py` (raw->marts refresh used by the Airflow DAG), `ssrf_guard.py` (validates any user-supplied URLs before fetching).
- `core/config.py` — `Settings` (pydantic-settings). Model provider/name resolution is layered: `MODEL_PROVIDER`+`MODEL_NAME` env vars, with secrets loadable from direct env vars, `*_FILE` paths, or a dotenv-style `QUERIO_SECRETS_FILE` (Docker mounts this at `/run/secrets/querio.env` so keys never need to live in `docker-compose.yml`/`.env`).
- `core/logging.py` — environment-aware logger: human-readable in dev (`DEBUG` default), structured JSON in prod (`INFO` default); overridable via `LOG_LEVEL`. Also writes to `backend/logs/querio.log`.

### Frontend (`frontend/src/`)

- `App.tsx` composes `ChatThread`/`ChatBubble` (conversation), `UploadZone` + `SchemaPreview` (CSV/JSON upload flow), `charts/ChartWidget.tsx` (Recharts).
- `api/askApi.ts`, `api/uploadApi.ts` — typed fetch wrappers around the backend REST endpoints; `types/api.ts` mirrors the backend's `schemas/`.
- Colocated `*.test.tsx`/`*.test.ts` next to source; Vitest + Testing Library, jsdom environment (`src/test/setup.ts`, shared fixtures in `src/test/mockData.ts`).

## Model provider configuration

Three interchangeable providers, switched via env config only (no UI dropdown):

| Provider | `MODEL_PROVIDER` | `MODEL_NAME` example | Secret |
|---|---|---|---|
| OpenAI | `openai` | `openai:gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `claude` | `anthropic:claude-3-5-sonnet-latest` | `ANTHROPIC_API_KEY` |
| Ollama (local) | `ollama` | uses `OLLAMA_MODEL`/`OLLAMA_BASE_URL` | none |

When no hosted key is present, the backend uses `FakeSqlGenerator` (a fixed canned query) instead of failing — this is intentional so the stack always boots; don't "fix" this by making startup fail on a missing key.

## Testing conventions

- Backend: unit tests use in-memory repositories and `FakeSqlGenerator`/dependency overrides (see `backend/tests/conftest.py`'s `client` fixture) rather than hitting a real Postgres or LLM API; integration tests under `tests/integration/` are the ones that assume a live Postgres.
- `tests/unit/test_golden_files.py` is a fuzz/golden-file suite over the upload ingestion pipeline (`csv_ingestion.py`) — check golden fixtures if it fails rather than assuming a fixture is stale.
- Frontend tests are colocated with components and use React Testing Library against real component trees, not shallow rendering.

## Security-relevant boundaries

- SQL guardrail (`guardrails/sql_validator.py`): SELECT-only, row cap, query timeout, executed under a read-only DB role. This is a hard boundary — no code path should send unvalidated SQL to Postgres.
- `services/ssrf_guard.py`: validates any user/LLM-supplied URL before the backend fetches it (relevant to the upload-by-URL flow) — extend this rather than adding a second, parallel fetch path.
- Querio is read-only by design: no write operations, no auth, no multi-tenancy (single-user POC).
