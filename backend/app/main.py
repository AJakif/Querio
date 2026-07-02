from dataclasses import dataclass
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.ask import router as ask_router
from app.services.ask_service import AskService
from app.core.config import settings
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


def _has_env(key: str) -> bool:
    from os import environ
    return key in environ and environ[key].strip() != ""


def _build_schema_repo() -> SchemaRepository:
    if _has_env("DATABASE_URL"):
        return PostgresSchemaRepository()
    return InMemorySchemaRepository()


def _build_query_repo() -> SchemaRepository:
    if _has_env("DATABASE_URL"):
        return PostgresQueryRepository()
    return InMemoryQueryRepository()


def _build_sql_generator(schema_repo: SchemaRepository) -> SqlGenerator:
    if _has_env("OPENAI_API_KEY") or _has_env("ANTHROPIC_API_KEY"):
        return PydanticAiSqlGenerator(settings.model_name, schema_repo)
    return FakeSqlGenerator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_state
    schema_repo = _build_schema_repo()
    query_repo = _build_query_repo()
    sql_generator = _build_sql_generator(schema_repo)
    app_state = AppState(
        ask_service=AskService(
            sql_generator=sql_generator,
            schema_repository=schema_repo,
            query_repository=query_repo,
        ),
    )
    yield
    app_state = None


app = FastAPI(title="Querio", lifespan=lifespan)

app.include_router(ask_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
