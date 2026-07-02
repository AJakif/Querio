from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://querio:querio@localhost:5432/querio"
    model_name: str = "openai:gpt-4o-mini"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434/v1"
    max_rows: int = 1000
    query_timeout_seconds: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
