from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


def _compose_text() -> str:
    return COMPOSE_FILE.read_text(encoding="utf-8")


def _service_body(compose: str, service_name: str) -> str:
    lines = compose.splitlines()
    start_index = lines.index(f"  {service_name}:") + 1
    collected: list[str] = []

    for line in lines[start_index:]:
        if line.startswith("  ") and not line.startswith("    "):
            break
        collected.append(line)

    return "\n".join(collected)


class TestLocalStackComposeContract:
    def test_compose_defines_reviewer_facing_services(self):
        compose = _compose_text()

        assert "services:" in compose
        assert "  postgres:\n" in compose
        assert "  airflow:\n" in compose
        assert "  backend:\n" in compose
        assert "  frontend:\n" in compose

    def test_core_services_have_healthchecks(self):
        compose = _compose_text()

        for service_name in ("postgres", "backend", "frontend"):
            service_body = _service_body(compose, service_name)
            assert "healthcheck:" in service_body, (
                f"{service_name} should declare a compose healthcheck so "
                "docker compose can report the local stack as healthy."
            )

    def test_backend_uses_marts_schema_after_dbt_runs(self):
        compose = _compose_text()
        backend_body = _service_body(compose, "backend")

        assert "DB_SCHEMA: marts" in backend_body
        assert "condition: service_completed_successfully" in backend_body

    def test_backend_uses_host_gateway_for_docker_ollama(self):
        compose = _compose_text()
        backend_body = _service_body(compose, "backend")

        assert "OLLAMA_BASE_URL_DOCKER" in backend_body
        assert "host.docker.internal:11434/v1" in backend_body

    def test_dbt_service_runs_tests_before_backend_starts(self):
        compose = _compose_text()
        dbt_body = _service_body(compose, "dbt")

        assert "dbt run &&" in dbt_body
        assert "dbt test" in dbt_body

    def test_dbt_project_keeps_models_in_plain_marts_schema(self):
        macro_path = REPO_ROOT / "dbt" / "macros" / "generate_schema_name.sql"

        assert macro_path.exists(), (
            "dbt should override schema-name generation so models build into "
            "the plain marts schema instead of an auto-prefixed variant."
        )

    def test_airflow_service_exposes_ui_and_mounts_repo_assets(self):
        compose = _compose_text()
        airflow_body = _service_body(compose, "airflow")

        assert '8081:8080' in airflow_body
        assert './infra/airflow/dags:/opt/airflow/dags' in airflow_body
        assert './backend:/opt/querio/backend' in airflow_body
        assert './dbt:/opt/querio/dbt' in airflow_body
        assert 'command: standalone' in airflow_body


class TestFrontendProxyContract:
    def test_nginx_preserves_api_prefix_when_proxying_to_backend(self):
        nginx_conf = (REPO_ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")

        assert "location /api/" in nginx_conf
        assert "proxy_pass http://backend:8000/api/;" in nginx_conf, (
            "The built frontend should forward /api requests to the backend "
            "without stripping the /api prefix."
        )


class TestReviewerDocsContract:
    def test_readme_documents_clone_to_first_question_flow(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        assert "cp .env.example .env" in readme
        assert "cp .env.secrets.example .env.secrets" in readme
        assert "docker compose up" in readme
        assert "http://localhost:3000" in readme
        assert "docker compose down" in readme
        assert "docker compose down --volumes" in readme

    def test_env_example_matches_documented_backend_model_settings(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        env_secrets_example = (REPO_ROOT / ".env.secrets.example").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        assert "MODEL_NAME=" in env_example
        assert "MODEL_PROVIDER=" in env_example
        assert "QUERIO_SECRETS_FILE=" in env_example
        assert "OPENAI_API_KEY=" in env_secrets_example
        assert "ANTHROPIC_API_KEY=" in env_secrets_example
        assert "MODEL_PROVIDER=" in readme

    def test_readme_documents_airflow_refresh_flow(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        assert "http://localhost:8081" in readme
        assert "scheduled_data_refresh" in readme
        assert "append_synthetic_orders.py" in readme
        assert "run history" in readme.lower()
