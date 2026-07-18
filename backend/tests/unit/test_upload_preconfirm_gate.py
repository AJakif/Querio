"""Load-bearing test: data stored via preview must not be queryable before confirm.

PRD US-24, SRS CONV-3: no session_id (and therefore no session schema) exists
until the client posts to /upload/confirm.  The preview token is the sole accessor
to the in-memory data — it is not a session_id.
"""
from app.services.session_manager import SessionManager
from app.services.csv_ingestion import InferredColumn, PreviewResult


def _make_preview() -> PreviewResult:
    col = InferredColumn(name="revenue", values=["100", "200"])
    return PreviewResult(columns=[col], all_rows=[{"revenue": "100"}, {"revenue": "200"}])


def test_preview_only_does_not_create_session():
    """store_preview must not materialise any DB schema or register any session.

    Only create_session_schema (called exclusively from /upload/confirm) registers a
    session_id.  Without confirm, no session_id exists to pass to /ask, so the
    uploaded rows are inaccessible by any /ask request.
    """
    mgr = SessionManager()
    token = mgr.store_preview(_make_preview())

    # Preview data is accessible via the token (not yet written to any DB schema)
    assert mgr.get_preview(token) is not None

    # No session was registered in either state dict — confirm was never called
    assert not mgr._session_notes
    assert not mgr._session_join_keys
