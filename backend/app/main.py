from dataclasses import dataclass
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.ask import router as ask_router
from app.services.ask_service import AskService
from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
from app.repositories.memory.query_repository_memory import InMemoryQueryRepository


@dataclass
class AppState:
    ask_service: AskService


app_state: AppState | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_state
    schema_repo = InMemorySchemaRepository()
    query_repo = InMemoryQueryRepository()
    app_state = AppState(
        ask_service=AskService(
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
