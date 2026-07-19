import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    from app.api.routes.ask import get_ask_service
    from app.api.deps import get_chat_history_service
    from app.agent.agent import FakeSqlGenerator
    from app.repositories.memory.query_repository_memory import InMemoryQueryRepository
    from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
    from app.repositories.memory.chat_history_repository_memory import InMemoryChatHistoryRepository
    from app.services.ask_service import AskService
    from app.services.chat_history_service import ChatHistoryService

    overrides_added: list = []

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
        overrides_added.append(get_ask_service)

    if get_chat_history_service not in app.dependency_overrides:
        _chat_service = ChatHistoryService(repo=InMemoryChatHistoryRepository())

        def _chat_override() -> ChatHistoryService:
            return _chat_service

        app.dependency_overrides[get_chat_history_service] = _chat_override
        overrides_added.append(get_chat_history_service)

    with TestClient(app) as c:
        yield c

    for dep in overrides_added:
        app.dependency_overrides.pop(dep, None)
