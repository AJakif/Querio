"""Load-bearing test: session teardown drops the DB schema and clears session state.

SRS CONV-3 privacy guarantee: DROP SCHEMA … CASCADE executes on teardown so
uploaded data cannot outlive the session.
"""
import pytest
import app.services.session_manager as sm_module
from app.services.session_manager import SessionManager


@pytest.mark.asyncio
async def test_teardown_drops_schema_and_clears_state(monkeypatch):
    """drop_session_schema must issue DROP SCHEMA … CASCADE and purge session notes/join keys."""
    executed: list[str] = []

    async def _fake_execute_ddl(sql: str) -> None:
        executed.append(sql)

    monkeypatch.setattr(sm_module, "_execute_ddl", _fake_execute_ddl)

    session_id = "abc-dead-beef-1234"
    mgr = SessionManager()
    mgr._session_notes[session_id] = "some context"
    mgr._session_join_keys[session_id] = ("customer_id", "fct_orders")

    await mgr.drop_session_schema(session_id)

    # The right DDL was issued
    assert any(
        "DROP SCHEMA" in sql and "session_abc_dead_beef_1234" in sql
        for sql in executed
    )
    # In-memory state cleared
    assert session_id not in mgr._session_notes
    assert session_id not in mgr._session_join_keys
