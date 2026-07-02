from app.repositories.base import QueryRepository


class FakeQueryRepository(QueryRepository):
    def __init__(self):
        self.executed_sql: list[str] = []
        self._rows_to_return: list[dict] = []

    def set_return_rows(self, rows: list[dict]):
        self._rows_to_return = rows

    async def execute(self, sql: str) -> list[dict]:
        self.executed_sql.append(sql)
        return self._rows_to_return
