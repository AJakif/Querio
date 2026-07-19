import asyncio
from dataclasses import dataclass
from contextlib import asynccontextmanager
from os import environ

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.api.routes.ask import router as ask_router
from app.api.routes.upload import router as upload_router
from app.api.routes.session import router as session_router
from app.api.routes.schema import router as schema_router
from app.api.routes.verification import router as verification_router
from app.api.routes.accounts import router as accounts_router
from app.services.ask_service import AskService
from app.services.chat_history_service import ChatHistoryService
from app.services.session_manager import SessionManager
from app.services.verification_service import VerificationService
from app.services.account_service import AccountService
from app.repositories.base import SchemaRepository, QueryRepository
from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
from app.repositories.memory.query_record_repository_memory import InMemoryQueryRecordRepository
from app.repositories.memory.account_repository_memory import InMemoryAccountRepository
from app.repositories.memory.chat_history_repository_memory import InMemoryChatHistoryRepository
from app.repositories.postgres.schema_repository_pg import PostgresSchemaRepository
from app.repositories.postgres.query_repository_pg import PostgresQueryRepository
from app.repositories.postgres.chat_history_repository_pg import PostgresChatHistoryRepository
from app.agent.agent import SqlGenerator, PydanticAiSqlGenerator, FakeSqlGenerator
from app.agent.aggregator import Aggregator, PydanticAiAggregator, FakeAggregator
from app.agent.planner import Planner, PydanticAiPlanner, FakePlanner
from app.agent.validator import Validator


@dataclass
class AppState:
    ask_service: AskService
    session_manager: SessionManager
    schema_repository: SchemaRepository
    query_repository: QueryRepository
    verification_service: VerificationService
    account_service: AccountService
    chat_history_service: ChatHistoryService


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


async def _build_chat_history_service() -> ChatHistoryService:
    if _has_env("DATABASE_URL"):
        from scripts.run_migrations import run_migrations
        try:
            await asyncio.to_thread(run_migrations)
        except Exception as exc:
            raise RuntimeError(f"Failed to apply chat history migrations: {exc}") from exc
        logger.info("Using Postgres chat history repository")
        return ChatHistoryService(repo=PostgresChatHistoryRepository())
    logger.warning("DATABASE_URL not set, using in-memory chat history repository")
    return ChatHistoryService(repo=InMemoryChatHistoryRepository())


def _build_sql_generator(schema_repo: SchemaRepository) -> SqlGenerator:
    if settings.effective_model_provider == "ollama" or settings.has_llm_api_key:
        logger.info(
            "Using provider-backed SQL generator",
            extra={
                "model_provider": settings.effective_model_provider,
                "model_name": settings.effective_model_name,
            },
        )
        return PydanticAiSqlGenerator(
            settings.effective_model_name,
            schema_repo,
            openai_api_key=settings.openai_api_key.get_secret_value() if settings.openai_api_key else None,
            anthropic_api_key=settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None,
            ollama_base_url=settings.ollama_base_url,
            ollama_num_ctx=settings.ollama_num_ctx,
        )
    logger.warning("No LLM API keys configured, using fake SQL generator")
    return FakeSqlGenerator()


def _build_planner(schema_repo: SchemaRepository) -> Planner:
    if settings.effective_model_provider == "ollama" or settings.has_llm_api_key:
        logger.info(
            "Using provider-backed planner",
            extra={
                "model_provider": settings.effective_model_provider,
                "model_name": settings.effective_model_name,
            },
        )
        return PydanticAiPlanner(
            settings.effective_model_name,
            schema_repo,
            openai_api_key=settings.openai_api_key.get_secret_value() if settings.openai_api_key else None,
            anthropic_api_key=settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None,
            ollama_base_url=settings.ollama_base_url,
            ollama_num_ctx=settings.ollama_num_ctx,
        )
    logger.warning("No LLM API keys configured, using fake planner")
    return FakePlanner()


def _build_aggregator() -> Aggregator:
    if settings.effective_model_provider == "ollama" or settings.has_llm_api_key:
        logger.info(
            "Using provider-backed aggregator",
            extra={
                "model_provider": settings.effective_model_provider,
                "model_name": settings.effective_model_name,
            },
        )
        return PydanticAiAggregator(
            settings.effective_model_name,
            openai_api_key=settings.openai_api_key.get_secret_value() if settings.openai_api_key else None,
            anthropic_api_key=settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None,
            ollama_base_url=settings.ollama_base_url,
            ollama_num_ctx=settings.ollama_num_ctx,
        )
    logger.warning("No LLM API keys configured, using fake aggregator")
    return FakeAggregator()


async def _verify_schema_ready(schema_repo: SchemaRepository) -> None:
    if not isinstance(schema_repo, PostgresSchemaRepository):
        return

    tables = await schema_repo.get_tables()
    if not tables:
        raise RuntimeError(
            f"Configured database schema '{settings.db_schema}' contains no tables. "
            "Ensure the seed and dbt steps completed successfully."
        )

    expected_tables_by_schema = {
        "marts": {"fct_orders", "dim_customers"},
    }
    expected_tables = expected_tables_by_schema.get(settings.db_schema, set())
    missing_tables = sorted(expected_tables - set(tables))
    if missing_tables:
        raise RuntimeError(
            f"Configured database schema '{settings.db_schema}' is missing expected tables: "
            f"{', '.join(missing_tables)}. Available tables: {', '.join(tables)}."
        )

    logger.info(
        "Verified database schema readiness",
        extra={"db_schema": settings.db_schema, "table_count": len(tables)},
    )


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
            "model_provider": settings.effective_model_provider,
        },
    )
    schema_repo, query_repo = _build_repos()
    await _verify_schema_ready(schema_repo)
    sql_generator = _build_sql_generator(schema_repo)
    planner = _build_planner(schema_repo)
    aggregator = _build_aggregator()
    validator = Validator()
    session_manager = SessionManager()
    query_record_repo = InMemoryQueryRecordRepository()
    account_repo = InMemoryAccountRepository()
    verification_service = VerificationService(repo=query_record_repo)
    chat_history_service = await _build_chat_history_service()
    app_state = AppState(
        ask_service=AskService(
            sql_generator=sql_generator,
            schema_repository=schema_repo,
            query_repository=query_repo,
            planner=planner,
            validator=validator,
            aggregator=aggregator,
            query_record_service=verification_service,
        ),
        session_manager=session_manager,
        schema_repository=schema_repo,
        query_repository=query_repo,
        verification_service=verification_service,
        account_service=AccountService(repo=account_repo),
        chat_history_service=chat_history_service,
    )
    yield
    logger.info("Shutting down Querio API")
    app_state = None


app = FastAPI(title="Querio", lifespan=lifespan)

app.include_router(ask_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(schema_router, prefix="/api")
app.include_router(verification_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
