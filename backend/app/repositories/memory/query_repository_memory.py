from app.repositories.base import QueryRepository
from app.core.logging import get_logger


logger = get_logger("repositories.memory.query")


class InMemoryQueryRepository(QueryRepository):
    def __init__(self):
        self.executed_sql: list[str] = []
        self._rows_to_return: list[dict] = []
        logger.info("Initialized in-memory query repository")

    def set_return_rows(self, rows: list[dict]):
        self._rows_to_return = rows
        logger.debug("Configured in-memory query rows", extra={"row_count": len(rows)})

    async def execute(self, sql: str) -> list[dict]:
        self.executed_sql.append(sql)
        logger.info("Executed in-memory query", extra={"sql": sql, "row_count": len(self._rows_to_return)})
        return self._rows_to_return
