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
2. **Seed** (`python scripts/load_raw.py`) creates the `raw` schema and populates 9 tables with deterministic Olist-like data.
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
SEED_DATABASE=false
DB_SCHEMA=marts
MODEL_PROVIDER=openai
MODEL_NAME=openai:gpt-4o-mini
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434/v1
LOG_LEVEL=
QUERIO_SECRETS_FILE=.env.secrets
```

`SEED_DATABASE` controls whether the Docker `seed` service loads Querio's bundled
deterministic demo dataset. It defaults to `false`, so your database is not
populated with demo rows automatically. Set `SEED_DATABASE=true` when you want
the included demo data; after changing it, recreate the seed and dbt services.

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

### Running with Ollama

Querio's agent pipeline chains several structured-output calls per question (ambiguity scoring, SQL generation, cost/fingerprint validation, AnswerSpec assembly with typed chart specs and citations), so the local model needs reliable function-calling / structured-output support, not just general chat quality — this is where small local models tend to fall apart first.

**Recommended model: `qwen2.5:7b`.** It has meaningfully better structured-output/tool-calling reliability than the repo's current default (`llama3.1:8b`) at a comparable footprint (~4.7GB Q4). Avoid going smaller (`llama3.2:3b`, `phi3-mini`, etc.) — sub-7B models tend to silently drift on JSON shape across a multi-step tool-call chain rather than fail obviously.

```bash
ollama pull qwen2.5:7b
```

Then set in `.env` (or `.env.secrets` is not needed here — Ollama requires no API key):

```bash
MODEL_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434/v1
```

`scripts/setup.sh` / `scripts/setup.ps1` auto-detect a running Ollama daemon and default `MODEL_PROVIDER=ollama` for a fresh `.env`, but they don't override `OLLAMA_MODEL` — it's still worth setting `OLLAMA_MODEL=qwen2.5:7b` by hand instead of the generated default (`llama3.1`).

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
