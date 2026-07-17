"""Load-bearing tests for Epic 10 Slice 18 — Local accounts.

Three acceptance criteria verified here:
1. Ask-without-account works (no auth required on /api/ask).
2. Verify-without-account returns 401 identity_required.
3. Verifying after account creation records the real username.
"""
import pytest
from fastapi.testclient import TestClient

from app.domain.exceptions import AccountExistsError, InvalidCredentialsError
from app.repositories.memory.account_repository_memory import InMemoryAccountRepository
from app.repositories.memory.query_record_repository_memory import InMemoryQueryRecordRepository
from app.services.account_service import AccountService
from app.services.verification_service import VerificationService


# ---------------------------------------------------------------------------
# AccountService unit tests
# ---------------------------------------------------------------------------


def make_account_service() -> AccountService:
    return AccountService(repo=InMemoryAccountRepository())


@pytest.mark.asyncio
async def test_first_account_becomes_owner():
    """First registered account gets is_owner=True."""
    svc = make_account_service()
    account, _ = await svc.register("alice", "password123")
    assert account.is_owner is True


@pytest.mark.asyncio
async def test_subsequent_account_not_owner():
    svc = make_account_service()
    await svc.register("alice", "password123")
    account, _ = await svc.register("bob", "password456")
    assert account.is_owner is False


@pytest.mark.asyncio
async def test_duplicate_username_raises():
    svc = make_account_service()
    await svc.register("alice", "password123")
    with pytest.raises(AccountExistsError):
        await svc.register("alice", "other")


@pytest.mark.asyncio
async def test_token_resolves_to_account():
    svc = make_account_service()
    _, token = await svc.register("alice", "password123")
    account = await svc.get_account_for_token(token)
    assert account is not None
    assert account.username == "alice"


@pytest.mark.asyncio
async def test_wrong_password_raises():
    svc = make_account_service()
    await svc.register("alice", "password123")
    with pytest.raises(InvalidCredentialsError):
        await svc.authenticate("alice", "wrongpass")


# ---------------------------------------------------------------------------
# HTTP endpoint acceptance tests
# ---------------------------------------------------------------------------


@pytest.fixture
def full_client():
    """Client with both account and verification services overridden (in-memory)."""
    from app.main import app
    from app.api.routes.verification import get_verification_service
    from app.api.deps import get_account_service

    query_repo = InMemoryQueryRecordRepository()
    v_service = VerificationService(repo=query_repo)
    acc_repo = InMemoryAccountRepository()
    a_service = AccountService(repo=acc_repo)

    async def _v_override() -> VerificationService:
        return v_service

    async def _a_override() -> AccountService:
        return a_service

    app.dependency_overrides[get_verification_service] = _v_override
    app.dependency_overrides[get_account_service] = _a_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_verification_service, None)
    app.dependency_overrides.pop(get_account_service, None)


def test_ask_works_without_account(full_client: TestClient):
    """AC: core ask loop requires no account."""
    resp = full_client.post("/api/ask", json={"question": "how many orders?"})
    # FakeSqlGenerator returns a canned answer — just verify auth is not blocking
    assert resp.status_code == 200


def test_verify_without_account_returns_identity_required(full_client: TestClient):
    """AC: verify without auth returns 401 identity_required."""
    # Register a query
    resp = full_client.post(
        "/api/queries",
        json={"sql": "SELECT 1", "author": "alice", "fingerprints": []},
    )
    assert resp.status_code == 201
    query_id = resp.json()["query_id"]

    # Attempt verify with no Authorization header
    resp = full_client.post(
        f"/api/queries/{query_id}/verify",
        json={"fingerprints": []},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "identity_required"


def test_verify_after_account_creation_records_username(full_client: TestClient):
    """AC: verifying after account creation records the real username as last_verifier."""
    # Register verifier account
    resp = full_client.post("/api/accounts", json={"username": "bob", "password": "password123"})
    assert resp.status_code == 201
    token = resp.json()["token"]
    assert resp.json()["is_owner"] is True  # first account is owner

    # Register a query by alice
    resp = full_client.post(
        "/api/queries",
        json={"sql": "SELECT 1", "author": "alice", "fingerprints": []},
    )
    query_id = resp.json()["query_id"]

    # Verify as bob
    resp = full_client.post(
        f"/api/queries/{query_id}/verify",
        json={"fingerprints": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["badge_state"] == "verified"
    assert resp.json()["last_verifier"] == "bob"
