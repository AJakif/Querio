import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    from app.api.routes.ask import get_ask_service
    from app.agent.agent import FakeSqlGenerator
    from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
    from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
    from app.services.ask_service import AskService

    did_override = False
    if get_ask_service not in app.dependency_overrides:
        schema_repo = InMemorySchemaRepository()
        query_repo = InMemoryQueryRepository()
        query_repo.set_return_rows([{"order_count": 10}])

        async def _override() -> AskService:
            return AskService(
                sql_generator=FakeSqlGenerator(),
                schema_repository=schema_repo,
                query_repository=query_repo,
            )

        app.dependency_overrides[get_ask_service] = _override
        did_override = True

    with TestClient(app) as c:
        yield c
    if did_override:
        app.dependency_overrides.pop(get_ask_service, None)
