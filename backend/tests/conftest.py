import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.fakes.fake_schema_repository import FakeSchemaRepository
from tests.fakes.fake_query_repository import FakeQueryRepository


@pytest.fixture
def fake_schema_repo() -> FakeSchemaRepository:
    return FakeSchemaRepository()


@pytest.fixture
def fake_query_repo() -> FakeQueryRepository:
    return FakeQueryRepository()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
