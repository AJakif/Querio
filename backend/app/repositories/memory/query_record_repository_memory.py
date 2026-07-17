from app.domain.models import QueryRecord
from app.repositories.base import QueryRecordRepository


class InMemoryQueryRecordRepository(QueryRecordRepository):
    def __init__(self) -> None:
        self._store: dict[str, QueryRecord] = {}

    async def get(self, query_id: str) -> QueryRecord | None:
        return self._store.get(query_id)

    async def save(self, record: QueryRecord) -> None:
        self._store[record.id] = record

    async def list_all(self) -> list[QueryRecord]:
        return list(self._store.values())
