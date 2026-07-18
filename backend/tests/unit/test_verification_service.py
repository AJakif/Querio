"""Tests for the verified-query lifecycle (badge-state transitions).

All tests assert end-to-end badge-state behaviour — not internal fingerprint
hash values — consistent with the acceptance criteria in Epic 9 Slice 5.
"""
import pytest
from fastapi.testclient import TestClient

from app.domain.exceptions import QueryNotFoundError, SelfVerifyError
from app.domain.models import BadgeState, Fingerprint
from app.repositories.memory.account_repository_memory import InMemoryAccountRepository
from app.repositories.memory.query_record_repository_memory import (
    InMemoryQueryRecordRepository,
)
from app.services.account_service import AccountService
from app.services.verification_service import VerificationService, _detect_drift


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_service() -> VerificationService:
    return VerificationService(repo=InMemoryQueryRecordRepository())


def fp(table: str, column: str, schema_hash: str, value_hash: str | None = None) -> Fingerprint:
    return Fingerprint(table=table, column=column, schema_hash=schema_hash, value_hash=value_hash)


BASELINE_FPS = [fp("orders", "status", "hash_v1", "vals_v1")]


# ---------------------------------------------------------------------------
# Service unit tests (9 load-bearing tests mapping 1:1 to acceptance criteria)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_query_starts_unverified():
    """AC: A new query starts in Unverified state."""
    svc = make_service()
    record = await svc.register_query("q1", "SELECT 1", "alice", BASELINE_FPS)
    assert record.badge_state() == BadgeState.unverified


@pytest.mark.asyncio
async def test_verify_moves_to_verified():
    """AC: Verifying a query requires a person's name and moves it to Verified."""
    svc = make_service()
    await svc.register_query("q1", "SELECT 1", "alice", BASELINE_FPS)
    record = await svc.verify("q1", "bob", BASELINE_FPS)
    assert record.badge_state() == BadgeState.verified
    last = record.last_verification()
    assert last is not None
    assert last.actor == "bob"


@pytest.mark.asyncio
async def test_self_verify_rejected():
    """AC: Author cannot verify their own query."""
    svc = make_service()
    await svc.register_query("q1", "SELECT 1", "alice", BASELINE_FPS)
    with pytest.raises(SelfVerifyError):
        await svc.verify("q1", "alice", BASELINE_FPS)


@pytest.mark.asyncio
async def test_dispute_outranks_verified():
    """AC: Flagging a Verified query as Disputed outranks Verified until re-verification."""
    svc = make_service()
    await svc.register_query("q1", "SELECT 1", "alice", BASELINE_FPS)
    await svc.verify("q1", "bob", BASELINE_FPS)
    record = await svc.dispute("q1", "carol")
    assert record.badge_state() == BadgeState.disputed


@pytest.mark.asyncio
async def test_structural_drift_triggers_needs_recheck():
    """AC: Structural fingerprint drift (schema_hash changed) moves Verified → Needs recheck."""
    svc = make_service()
    await svc.register_query("q1", "SELECT 1", "alice", BASELINE_FPS)
    await svc.verify("q1", "bob", BASELINE_FPS)

    drifted = [fp("orders", "status", "hash_v2", "vals_v1")]  # schema_hash changed
    record, reasons = await svc.check_drift("q1", drifted)

    assert record.badge_state() == BadgeState.needs_recheck
    assert any("orders.status schema changed" in r for r in reasons)


@pytest.mark.asyncio
async def test_semantic_drift_triggers_needs_recheck():
    """AC: New distinct value in a fingerprinted filter column triggers Needs recheck."""
    svc = make_service()
    await svc.register_query("q1", "SELECT 1", "alice", BASELINE_FPS)
    await svc.verify("q1", "bob", BASELINE_FPS)

    drifted = [fp("orders", "status", "hash_v1", "vals_v2")]  # value_hash changed
    record, reasons = await svc.check_drift("q1", drifted)

    assert record.badge_state() == BadgeState.needs_recheck
    assert any("orders.status has a new value" in r for r in reasons)


@pytest.mark.asyncio
async def test_export_import_roundtrip_matching_fingerprints():
    """Round-trip: verified record exported and re-imported with same fingerprints stays verified (SRS VQ-6)."""
    svc_a = make_service()
    await svc_a.register_query("q1", "SELECT 1", "alice", BASELINE_FPS)
    await svc_a.verify("q1", "bob", BASELINE_FPS)

    portable = await svc_a.export_portable("q1")

    svc_b = make_service()
    imported = await svc_b.import_portable(portable, current_fingerprints=BASELINE_FPS)

    assert imported.badge_state() == BadgeState.verified
    assert imported.id == "q1"
    assert imported.sql == "SELECT 1"
    # Exactly 1 history event (the verify); no needs_recheck appended
    assert len(imported.history) == 1


@pytest.mark.asyncio
async def test_import_marks_needs_recheck_on_schema_mismatch():
    """Imported verified record with differing schema_hash arrives as needs_recheck (SRS VQ-6)."""
    svc_a = make_service()
    await svc_a.register_query("q1", "SELECT 1", "alice", BASELINE_FPS)
    await svc_a.verify("q1", "bob", BASELINE_FPS)

    portable = await svc_a.export_portable("q1")

    svc_b = make_service()
    stale_fps = [fp("orders", "status", "hash_v2", "vals_v1")]  # schema_hash differs
    imported = await svc_b.import_portable(portable, current_fingerprints=stale_fps)

    assert imported.badge_state() == BadgeState.needs_recheck


@pytest.mark.asyncio
async def test_reverify_after_needs_recheck_restores_verified():
    """AC (end-to-end): schema change → Needs recheck → re-verify → Verified."""
    svc = make_service()
    await svc.register_query("q1", "SELECT 1", "alice", BASELINE_FPS)
    await svc.verify("q1", "bob", BASELINE_FPS)

    # Drift triggers Needs recheck
    drifted = [fp("orders", "status", "hash_v2", "vals_v1")]
    record, _ = await svc.check_drift("q1", drifted)
    assert record.badge_state() == BadgeState.needs_recheck

    # Re-verification with updated fingerprints restores Verified
    record = await svc.verify("q1", "bob", drifted)
    assert record.badge_state() == BadgeState.verified


# ---------------------------------------------------------------------------
# HTTP endpoint smoke tests
# ---------------------------------------------------------------------------


@pytest.fixture
def v_client():
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


def test_verify_endpoint_happy_path(v_client: TestClient):
    """Endpoint POST /api/queries/{id}/verify returns badge_state=verified."""
    # Create bob's account and get a token
    resp = v_client.post("/api/accounts", json={"username": "bob", "password": "securepass"})
    assert resp.status_code == 201
    bob_token = resp.json()["token"]

    # Register a query authored by alice
    resp = v_client.post(
        "/api/queries",
        json={"sql": "SELECT 1", "author": "alice", "fingerprints": []},
    )
    assert resp.status_code == 201
    query_id = resp.json()["query_id"]

    # Verify as bob (authenticated)
    resp = v_client.post(
        f"/api/queries/{query_id}/verify",
        json={"fingerprints": []},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["badge_state"] == "verified"
    assert resp.json()["last_verifier"] == "bob"


def test_self_verify_endpoint_returns_400(v_client: TestClient):
    """Endpoint rejects self-verification with 400."""
    # alice registers and gets a token
    resp = v_client.post("/api/accounts", json={"username": "alice", "password": "securepass"})
    alice_token = resp.json()["token"]

    resp = v_client.post(
        "/api/queries",
        json={"sql": "SELECT 1", "author": "alice", "fingerprints": []},
    )
    query_id = resp.json()["query_id"]

    resp = v_client.post(
        f"/api/queries/{query_id}/verify",
        json={"fingerprints": []},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert resp.status_code == 400
    assert "cannot verify" in resp.json()["detail"].lower()
