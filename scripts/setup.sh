#!/usr/bin/env bash
# Querio first-run setup: generates .env / .env.secrets from the .example
# templates and auto-detects a local Ollama instance so a first query is
# reachable with zero external accounts or API keys (Epic 8, Slice 17).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Overridable for tests / alternate layouts; not part of the normal CLI surface.
OUTPUT_DIR="${QUERIO_SETUP_OUTPUT_DIR:-$REPO_ROOT}"
OLLAMA_PROBE_URL="${QUERIO_OLLAMA_PROBE_URL:-http://localhost:11434}"

FORCE=0
SMALL_MODEL=0

show_help() {
  cat <<'EOF'
Querio first-run setup

Usage:
  ./scripts/setup.sh [--force] [--small-model] [-h|--help]

Generates .env and .env.secrets from the .env.example / .env.secrets.example
templates (skips any file that already exists, so it's safe to re-run).

Probes for a local Ollama instance at http://localhost:11434. If found, the
generated .env defaults MODEL_PROVIDER=ollama with a working OLLAMA_BASE_URL
so you can ask your first question without any API key or account. If not
found, .env keeps the default (openai) provider — set an API key in
.env.secrets, or leave it blank to run against the built-in FakeSqlGenerator.

Options:
  --force        Overwrite existing .env / .env.secrets instead of skipping them.
  --small-model  Apply conservative context-knob values suited for local models
                 with an 8192-token context window (MAX_RESULT_ROWS=200,
                 MAX_LLM_ROWS=20, SESSION_BRIEF_MAX_TOKENS=150). Always applied
                 to .env when this flag is passed, even if .env already existed.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --small-model) SMALL_MODEL=1 ;;
    -h|--help) show_help; exit 0 ;;
    *)
      echo "Unknown option: $arg" >&2
      show_help
      exit 1
      ;;
  esac
done

ENV_EXAMPLE="${REPO_ROOT}/.env.example"
SECRETS_EXAMPLE="${REPO_ROOT}/.env.secrets.example"
ENV_FILE="${OUTPUT_DIR}/.env"
SECRETS_FILE="${OUTPUT_DIR}/.env.secrets"

# Detect a running local Ollama at the standard endpoint. Tries /api/tags
# first, falls back to /api/version — either confirms a live daemon.
detect_ollama() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 2 "${url}/api/tags" >/dev/null 2>&1 && return 0
    curl -fsS --max-time 2 "${url}/api/version" >/dev/null 2>&1 && return 0
  fi
  return 1
}

# Copies src -> dest unless dest exists and FORCE=0. Echoes result, returns
# 0 if the file was (re)written, 1 if it was left alone.
copy_if_needed() {
  local src="$1" dest="$2"
  if [[ -f "$dest" && "$FORCE" -ne 1 ]]; then
    echo "Skipping $(basename "$dest") — already exists (use --force to overwrite)."
    return 1
  fi
  cp "$src" "$dest"
  echo "Created $(basename "$dest") from $(basename "$src")."
  return 0
}

# Sets KEY=VALUE in a dotenv-style file, replacing an existing line or
# appending a new one. Portable (no GNU/BSD sed divergence).
set_env_var() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file"; then
    awk -v k="$key" -v v="$value" 'BEGIN{FS=OFS="="} $1==k{$0=k"="v} {print}' "$file" > "${file}.tmp"
    mv "${file}.tmp" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

mkdir -p "$OUTPUT_DIR"

env_written=0
copy_if_needed "$ENV_EXAMPLE" "$ENV_FILE" && env_written=1 || true
copy_if_needed "$SECRETS_EXAMPLE" "$SECRETS_FILE" || true

if detect_ollama "$OLLAMA_PROBE_URL"; then
  echo "Detected a local Ollama instance at ${OLLAMA_PROBE_URL}."
  if [[ "$env_written" -eq 1 ]]; then
    set_env_var "$ENV_FILE" "MODEL_PROVIDER" "ollama"
    set_env_var "$ENV_FILE" "OLLAMA_BASE_URL" "${OLLAMA_PROBE_URL}/v1"
    echo "Configured MODEL_PROVIDER=ollama in .env — no API key needed."
  else
    echo ".env already existed and was left untouched. Set MODEL_PROVIDER=ollama yourself if you want to use it."
  fi
else
  echo "No local Ollama instance detected at ${OLLAMA_PROBE_URL}."
  echo "Falling back to existing behavior: add an OPENAI_API_KEY or ANTHROPIC_API_KEY to .env.secrets,"
  echo "or leave both blank to run against the built-in FakeSqlGenerator."
fi

if [[ "$SMALL_MODEL" -eq 1 ]]; then
  # Conservative row/token caps for local models with ≤8192-token context windows.
  # MAX_RESULT_ROWS=200  — limits raw DB result size; the default 1000 can overwhelm small models.
  # MAX_LLM_ROWS=20     — rows serialized into the LLM prompt; 20×~45 tokens ≈ 900 tokens,
  #                       leaving headroom for system prompt + schema + question + response.
  # SESSION_BRIEF_MAX_TOKENS=150 — halves the default 300-token brief to save context space.
  set_env_var "$ENV_FILE" "MAX_RESULT_ROWS" "200"
  set_env_var "$ENV_FILE" "MAX_LLM_ROWS" "20"
  set_env_var "$ENV_FILE" "SESSION_BRIEF_MAX_TOKENS" "150"
  echo "Applied small-model profile to .env (MAX_RESULT_ROWS=200, MAX_LLM_ROWS=20, SESSION_BRIEF_MAX_TOKENS=150)."
fi

echo ""
echo "Setup complete. Next: docker compose up (or ./scripts/querio.sh up)."
