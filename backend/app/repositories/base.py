from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.logging import get_logger


logger = get_logger("repositories.base")


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool


@dataclass
class RelationshipInfo:
    source_table: str
    source_column: str
    target_table: str
    target_column: str


class SchemaRepository(ABC):
    @abstractmethod
    async def get_tables(self) -> list[str]:
        ...

    @abstractmethod
    async def get_columns(self, table: str) -> list[ColumnInfo]:
        ...

    @abstractmethod
    async def get_relationships(self) -> list[RelationshipInfo]:
        ...


class QueryRepository(ABC):
    @abstractmethod
    async def execute(self, sql: str) -> list[dict]:
        ...
