# Setup

## Prerequisites

- Docker & Docker Compose
- Git

## Quick start

```bash
git clone <repo-url>
cd querio
cp .env.example .env
cp .env.secrets.example .env.secrets
docker compose up
```

Then open `http://localhost:3000` and start asking questions.

## Helper scripts

Windows/PowerShell:

```powershell
.\scripts\querio.ps1 up           # start the stack
.\scripts\querio.ps1 up -Detached # start in background
.\scripts\querio.ps1 down         # stop the stack
.\scripts\querio.ps1 logs         # view logs
.\scripts\querio.ps1 ps           # view running services
.\scripts\querio.ps1 reset        # reset data
.\scripts\querio.ps1 rebuild      # destructive: remove containers, volumes, images, then fresh build
```

Linux/macOS:

```bash
./scripts/querio.sh up         # start the stack
./scripts/querio.sh up -d      # start in background
./scripts/querio.sh down       # stop the stack
./scripts/querio.sh logs       # view logs
./scripts/querio.sh ps         # view running services
./scripts/querio.sh reset      # reset data
./scripts/querio.sh rebuild    # destructive rebuild
```

`rebuild` removes the Compose containers, volumes, and images for this stack, then runs a fresh `docker compose up --build --force-recreate`.

## Startup sequence

`docker compose up` runs the full pipeline automatically:

1. **Postgres** starts and waits for health.
2. **Seed** (`python scripts/load_raw.py`) creates the empty `raw` schema (9 tables, matching the Olist Brazilian E-Commerce structure) with no data.
3. **dbt** runs `dbt run`, which transforms `raw` → `marts` schema producing two analytical models:
   - `fct_orders` — order-level fact table (orders + items + payments)
   - `dim_customers` — customer dimension with aggregated order metrics
4. **Airflow** starts at `http://localhost:8081` and loads the `scheduled_data_refresh` DAG.
5. **Backend** starts, configured to read schema from the `marts` schema (`DB_SCHEMA=marts`).
6. **Frontend** starts, serving the chat UI.

The agent queries the clean `marts` schema tables — not the raw normalized tables — so joins are simpler and query generation is more reliable.

## Configuration

### Environment variables

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

The `seed` service only creates the empty `raw` schema (so dbt has tables to
build `marts` from) — it does not load any demo data. Load your own data via
the in-chat upload flow, or `INSERT` into the `raw` tables directly if you
want a persistent default dataset instead of a per-session upload.

```bash
# .env.secrets
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### Model configuration

| Provider | `MODEL_PROVIDER` | `MODEL_NAME` | Required secret |
|---|---|---|---|
| OpenAI | `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic Claude | `claude` | `claude-3-5-sonnet-latest` | `ANTHROPIC_API_KEY` |
| Ollama (local) | `ollama` | (uses `OLLAMA_MODEL`) | None |

The backend loads secrets in this order:

- Direct env vars like `OPENAI_API_KEY`
- File paths like `OPENAI_API_KEY_FILE`
- The dotenv-style file pointed to by `QUERIO_SECRETS_FILE`

The default Docker setup mounts `./.env.secrets` read-only into the container and reads `/run/secrets/querio.env`, so provider keys do not need to appear in `docker-compose.yml` or your main `.env`.

If hosted provider API keys are blank, Querio falls back to its built-in fake SQL generator so the local stack can still boot for wiring checks. Real natural-language SQL generation requires a valid hosted provider API key or a reachable local Ollama server.

### Context knobs

Three env vars control how much data flows through the pipeline. Set them in `.env`.

| Env var | Default | Controls |
|---|---|---|
| `MAX_RESULT_ROWS` | `1000` | Hard cap on rows the SQL guardrail allows the database to return. Queries that would exceed this are rejected before execution. |
| `MAX_LLM_ROWS` | `50` | Rows actually serialized into any LLM prompt. Enforced by `agent/prompt_gate.py` — the sole legal path for row data entering a prompt. |
| `SESSION_BRIEF_MAX_TOKENS` | `300` | Max tokens for the rolling session brief injected into Aggregator prompts. |

On models with small context windows (≤4B parameters, `OLLAMA_NUM_CTX=8192`), Querio may be slow but must never fail with a context-overflow error. If you see truncation or silent degradation, lower these values. The `--small-model` / `-SmallModel` flag in the setup scripts applies a pre-tuned conservative profile in one step:

```bash
# Bash / Linux / macOS
./scripts/setup.sh --small-model

# PowerShell / Windows
.\scripts\setup.ps1 -SmallModel
```

This sets `MAX_RESULT_ROWS=200`, `MAX_LLM_ROWS=20`, and `SESSION_BRIEF_MAX_TOKENS=150` in your `.env`. The flag can be combined with `--force` / `-Force` to regenerate `.env` from scratch at the same time.

### Running with Ollama

Querio's agent pipeline chains several structured-output calls per question (ambiguity scoring, SQL generation, cost/fingerprint validation, AnswerSpec assembly with typed chart specs and citations), so the local model needs reliable function-calling / structured-output support, not just general chat quality — this is where small local models tend to fall apart first.

**Minimum recommendation: `gemma4:e4b`.** In practice this is the smallest model that reliably completes the full pipeline (Planner → SQL Generator → Validator → Aggregator) with a proper structured AnswerSpec — badge, headline, restatement, chart/claims when applicable — instead of silently degrading to a plain-text fallback answer. It's a larger download (~9.6GB) and noticeably slower per call than `qwen2.5:7b` on CPU, so expect chart-eligible answers (which require a more complex Aggregator response) to take several minutes on modest hardware; budget your timeouts accordingly.

`qwen2.5:7b` (~4.7GB Q4) is a faster, lighter fallback with meaningfully better structured-output/tool-calling reliability than the repo's original default (`llama3.1:8b`), but it degrades to the plain-text fallback answer noticeably more often than `gemma4:e4b` on the Aggregator's structured-output step — expect fewer full AnswerCards. Avoid going smaller still (`llama3.2:3b`, `phi3-mini`, etc.) — sub-7B models tend to silently drift on JSON shape across a multi-step tool-call chain rather than fail obviously.

```bash
ollama pull gemma4:e4b
```

Then set in `.env` (or `.env.secrets` is not needed here — Ollama requires no API key):

```bash
MODEL_PROVIDER=ollama
OLLAMA_MODEL=gemma4:e4b
OLLAMA_BASE_URL=http://localhost:11434/v1
```

`scripts/setup.sh` / `scripts/setup.ps1` auto-detect a running Ollama daemon and default `MODEL_PROVIDER=ollama` for a fresh `.env`, but they don't override `OLLAMA_MODEL` — it's still worth setting `OLLAMA_MODEL=gemma4:e4b` by hand instead of the generated default (`llama3.1`).

## Logging

The backend logger is environment-aware:

- `APP_ENV=dev` uses a human-readable console format and defaults to `DEBUG`
- `APP_ENV=prod` uses structured JSON logs and defaults to `INFO`
- Logs are also written to `backend/logs/querio.log`
- `LOG_LEVEL` can override either default when you need a specific level

## Resetting data

```bash
docker compose down --volumes
```

This fully resets Postgres data and triggers a clean re-seed on the next startup.

For a full destructive rebuild:

```bash
docker compose down --volumes
docker compose up --build --force-recreate
```
