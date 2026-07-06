from pathlib import Path

from dotenv import dotenv_values
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(path: str | None) -> Path | None:
    if not path:
        return None

    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    project_candidate = PROJECT_ROOT / candidate
    if project_candidate.exists():
        return project_candidate

    backend_candidate = BACKEND_ROOT / candidate
    if backend_candidate.exists():
        return backend_candidate

    return project_candidate


def _read_secret_text(path: str | None) -> str | None:
    secret_path = _resolve_path(path)
    if not secret_path:
        return None

    if not secret_path.is_file():
        return None

    value = secret_path.read_text(encoding="utf-8").strip()
    return value or None


def _read_secrets_env(path: str | None) -> dict[str, str]:
    secrets_path = _resolve_path(path)
    if not secrets_path:
        return {}

    if not secrets_path.is_file():
        return {}

    return {
        key: value
        for key, value in dotenv_values(secrets_path).items()
        if isinstance(value, str) and value.strip()
    }


class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str = "postgresql://querio:querio@localhost:5432/querio"
    database_url_file: str | None = None
    model_provider: str | None = None
    model_name: str = "openai:gpt-4o-mini"
    ollama_model: str = "llama3.1"
    ollama_base_url: str = "http://localhost:11434/v1"
    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    openai_api_key_file: str | None = None
    anthropic_api_key: SecretStr | None = Field(default=None, repr=False)
    anthropic_api_key_file: str | None = None
    querio_secrets_file: str = str(PROJECT_ROOT / ".env.secrets")
    log_level: str | None = None
    max_rows: int = 1000
    query_timeout_ms: int = 5000
    db_schema: str = "marts"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def has_llm_api_key(self) -> bool:
        return bool(
            (self.openai_api_key and self.openai_api_key.get_secret_value())
            or (self.anthropic_api_key and self.anthropic_api_key.get_secret_value())
        )

    @property
    def normalized_app_env(self) -> str:
        value = self.app_env.strip().lower()
        if value in {"production", "prod"}:
            return "prod"
        return "dev"

    @property
    def effective_log_level(self) -> str:
        if self.log_level and self.log_level.strip():
            if self.normalized_app_env == "prod" and self.log_level.strip().upper() == "DEBUG":
                return "INFO"
            return self.log_level.strip().upper()
        if self.normalized_app_env == "prod":
            return "INFO"
        return "DEBUG"

    @property
    def effective_model_provider(self) -> str:
        if self.model_provider and self.model_provider.strip():
            return self.model_provider.strip().lower()

        provider, separator, _ = self.model_name.partition(":")
        if separator:
            if provider == "anthropic":
                return "claude"
            return provider.lower()
        return "openai"

    @property
    def effective_model_name(self) -> str:
        provider = self.effective_model_provider
        if provider == "ollama":
            return f"ollama:{self.ollama_model}"

        if self.model_provider and self.model_provider.strip():
            provider_prefix = "anthropic" if provider == "claude" else provider
            _, separator, raw_model = self.model_name.partition(":")
            model = raw_model if separator else self.model_name
            return f"{provider_prefix}:{model}"

        return self.model_name


def _apply_secret_overrides(base_settings: Settings) -> Settings:
    secret_env = _read_secrets_env(base_settings.querio_secrets_file)
    updates: dict[str, str | SecretStr] = {}

    database_url = _read_secret_text(base_settings.database_url_file)
    if database_url:
        updates["database_url"] = database_url

    if not base_settings.openai_api_key:
        openai_api_key = _read_secret_text(base_settings.openai_api_key_file) or secret_env.get("OPENAI_API_KEY")
        if openai_api_key:
            updates["openai_api_key"] = SecretStr(openai_api_key)

    if not base_settings.anthropic_api_key:
        anthropic_api_key = _read_secret_text(base_settings.anthropic_api_key_file) or secret_env.get("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            updates["anthropic_api_key"] = SecretStr(anthropic_api_key)

    return base_settings.model_copy(update=updates)


settings = _apply_secret_overrides(Settings())
