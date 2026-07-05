from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://querio:querio@localhost:5432/querio"
    model_name: str = "openai:gpt-4o-mini"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    max_rows: int = 1000
    db_schema: str = "marts"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
