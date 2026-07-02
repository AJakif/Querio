from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool


class SchemaRepository(ABC):
    @abstractmethod
    async def get_tables(self) -> list[str]:
        ...

    @abstractmethod
    async def get_columns(self, table: str) -> list[ColumnInfo]:
        ...


class QueryRepository(ABC):
    @abstractmethod
    async def execute(self, sql: str) -> list[dict]:
        ...
