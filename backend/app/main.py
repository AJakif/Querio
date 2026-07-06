from dataclasses import dataclass
from contextlib import asynccontextmanager
from os import environ

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.api.routes.ask import router as ask_router
from app.services.ask_service import AskService
from app.repositories.base import SchemaRepository, QueryRepository
from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository
from app.repositories.postgres.query_repository_pg import PostgresQueryRepository
from app.agent.agent import SqlGenerator, PydanticAiSqlGenerator, FakeSqlGenerator


@dataclass
class AppState:
    ask_service: AskService


app_state: AppState | None = None
logger = get_logger("main")


def _has_env(key: str) -> bool:
    return key in environ and environ[key].strip() != ""


def _build_repos() -> tuple[SchemaRepository, QueryRepository]:
    if _has_env("DATABASE_URL"):
        logger.info("Using Postgres repositories", extra={"db_schema": settings.db_schema})
        return PostgresSchemaRepository(schema=settings.db_schema), PostgresQueryRepository()
    logger.warning("DATABASE_URL not set, using in-memory repositories")
    return InMemorySchemaRepository(), InMemoryQueryRepository()


def _build_sql_generator(schema_repo: SchemaRepository) -> SqlGenerator:
    if settings.has_llm_api_key:
        logger.info("Using provider-backed SQL generator", extra={"model_name": settings.model_name})
        return PydanticAiSqlGenerator(
            settings.model_name,
            schema_repo,
            openai_api_key=settings.openai_api_key.get_secret_value() if settings.openai_api_key else None,
            anthropic_api_key=settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None,
        )
    logger.warning("No LLM API keys configured, using fake SQL generator")
    return FakeSqlGenerator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_state
    configure_logging(settings)
    logger.info(
        "Starting Querio API",
        extra={
            "app_env": settings.normalized_app_env,
            "db_schema": settings.db_schema,
            "llm_enabled": settings.has_llm_api_key,
        },
    )
    schema_repo, query_repo = _build_repos()
    sql_generator = _build_sql_generator(schema_repo)
    app_state = AppState(
        ask_service=AskService(
            sql_generator=sql_generator,
            schema_repository=schema_repo,
            query_repository=query_repo,
        ),
    )
    yield
    logger.info("Shutting down Querio API")
    app_state = None


app = FastAPI(title="Querio", lifespan=lifespan)

app.include_router(ask_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
