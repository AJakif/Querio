#!/usr/bin/env bash

set -euo pipefail

ACTION="${1:-up}"
DETACHED="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

show_help() {
  cat <<'EOF'
Querio local stack helper

Usage:
  ./scripts/querio.sh up           # start the full stack
  ./scripts/querio.sh up -d        # start in background
  ./scripts/querio.sh down         # stop and remove containers
  ./scripts/querio.sh stop         # alias for down
  ./scripts/querio.sh reset        # stop everything and delete volumes
  ./scripts/querio.sh rebuild      # delete containers, volumes, images, then rebuild from scratch
  ./scripts/querio.sh logs         # stream logs
  ./scripts/querio.sh ps           # show container status
  ./scripts/querio.sh help         # show this help
EOF
}

run_compose() {
  (
    cd "${REPO_ROOT}"
    docker compose "$@"
  )
}

if [[ "${ACTION}" == "help" ]]; then
  show_help
  exit 0
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose is not available. Install Docker Desktop or Docker Compose and make sure 'docker compose' works first." >&2
  exit 1
fi

case "${ACTION}" in
  up)
    args=(up)
    if [[ "${DETACHED}" == "-d" || "${DETACHED}" == "--detached" ]]; then
      args+=(-d)
    elif [[ -n "${DETACHED}" ]]; then
      echo "Unknown option for 'up': ${DETACHED}" >&2
      exit 1
    fi

    run_compose "${args[@]}"

    if [[ "${DETACHED}" == "-d" || "${DETACHED}" == "--detached" ]]; then
      echo
      echo "Querio is starting in the background."
    fi

    echo "Frontend: http://localhost:3000"
    echo "Backend:  http://localhost:8000/docs"
    echo "Airflow:  http://localhost:8081"
    ;;
  down)
    run_compose down
    ;;
  stop)
    run_compose down
    ;;
  reset)
    run_compose down --volumes
    ;;
  rebuild)
    run_compose down --volumes --rmi all --remove-orphans

    args=(up --build --force-recreate)
    if [[ "${DETACHED}" == "-d" || "${DETACHED}" == "--detached" ]]; then
      args+=(-d)
    elif [[ -n "${DETACHED}" ]]; then
      echo "Unknown option for 'rebuild': ${DETACHED}" >&2
      exit 1
    fi

    run_compose "${args[@]}"

    if [[ "${DETACHED}" == "-d" || "${DETACHED}" == "--detached" ]]; then
      echo
      echo "Querio has been rebuilt and is starting in the background."
    fi

    echo "Frontend: http://localhost:3000"
    echo "Backend:  http://localhost:8000/docs"
    echo "Airflow:  http://localhost:8081"
    ;;
  logs)
    run_compose logs -f
    ;;
  ps)
    run_compose ps
    ;;
  *)
    echo "Unknown action: ${ACTION}" >&2
    echo
    show_help
    exit 1
    ;;
esac
