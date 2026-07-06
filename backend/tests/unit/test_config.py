from pathlib import Path

from app.core.config import Settings, _apply_secret_overrides, _read_secrets_env


def test_secret_file_populates_api_keys(tmp_path: Path):
    secret_file = tmp_path / "querio.env"
    secret_file.write_text(
        "OPENAI_API_KEY=test-openai-key\nANTHROPIC_API_KEY=test-anthropic-key\n",
        encoding="utf-8",
    )

    settings = _apply_secret_overrides(
        Settings(
            querio_secrets_file=str(secret_file),
            openai_api_key=None,
            anthropic_api_key=None,
        )
    )

    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "test-openai-key"
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "test-anthropic-key"


def test_explicit_env_values_win_over_secret_file(tmp_path: Path):
    secret_file = tmp_path / "querio.env"
    secret_file.write_text("OPENAI_API_KEY=file-key\n", encoding="utf-8")

    settings = _apply_secret_overrides(
        Settings(
            querio_secrets_file=str(secret_file),
            openai_api_key="env-key",
        )
    )

    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "env-key"


def test_default_log_level_depends_on_environment():
    dev_settings = Settings(app_env="dev")
    prod_settings = Settings(app_env="prod")

    assert dev_settings.normalized_app_env == "dev"
    assert dev_settings.effective_log_level == "DEBUG"
    assert prod_settings.normalized_app_env == "prod"
    assert prod_settings.effective_log_level == "INFO"


def test_explicit_log_level_overrides_environment_default():
    settings = Settings(app_env="prod", log_level="warning")

    assert settings.effective_log_level == "WARNING"


def test_read_secrets_env_resolves_relative_path_from_project_root(tmp_path: Path, monkeypatch):
    project_root = tmp_path / "project"
    backend_root = project_root / "backend"
    backend_root.mkdir(parents=True)
    secret_file = project_root / ".env.secrets"
    secret_file.write_text("OPENAI_API_KEY=test-openai-key\n", encoding="utf-8")

    monkeypatch.setattr("app.core.config.PROJECT_ROOT", project_root)
    monkeypatch.setattr("app.core.config.BACKEND_ROOT", backend_root)

    secret_env = _read_secrets_env(".env.secrets")

    assert secret_env["OPENAI_API_KEY"] == "test-openai-key"
