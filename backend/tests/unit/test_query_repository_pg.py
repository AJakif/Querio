import pytest

from app.repositories.postgres.query_repository_pg import PostgresQueryRepository


class RecordingCursor:
    def __init__(self):
        self.calls: list[tuple[str, tuple | None]] = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return [{"val": 1}]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor):
        self._cursor = cursor

    def cursor(self, cursor_factory=None):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_execute_sets_search_path_before_query():
    cursor = RecordingCursor()
    conn = RecordingConnection(cursor)
    repo = PostgresQueryRepository(connection_factory=lambda: conn)

    rows = await repo.execute("SELECT 1 AS val")

    assert rows == [{"val": 1}]
    assert cursor.calls[0] == ("SET TRANSACTION READ ONLY", None)
    assert cursor.calls[1] == ("SELECT set_config('search_path', %s, true)", ("marts,public",))
    assert cursor.calls[2][0] == "SET LOCAL statement_timeout = %s"
    assert cursor.calls[3] == ("SELECT 1 AS val", None)
