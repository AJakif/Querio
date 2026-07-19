from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.domain.models import Account, ChatSession, QueryRecord, StoredTurn


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


class QueryRecordRepository(ABC):
    @abstractmethod
    async def get(self, query_id: str) -> QueryRecord | None:
        ...

    @abstractmethod
    async def save(self, record: QueryRecord) -> None:
        ...

    @abstractmethod
    async def list_all(self) -> list[QueryRecord]:
        ...


class ChatHistoryRepository(ABC):
    @abstractmethod
    async def create_session(
        self,
        account_username: str | None,
        upload_session_id: str | None,
    ) -> "ChatSession": ...

    @abstractmethod
    async def get_session(self, session_id: str) -> "ChatSession | None": ...

    @abstractmethod
    async def append_turn(
        self,
        session_id: str,
        question_text: str,
        answer_json: dict[str, Any],
    ) -> "StoredTurn": ...

    @abstractmethod
    async def list_turns(self, session_id: str) -> "list[StoredTurn]": ...

    @abstractmethod
    async def list_sessions(
        self, account_username: str | None
    ) -> "list[ChatSession]": ...


class AccountRepository(ABC):
    @abstractmethod
    async def get_by_username(self, username: str) -> Account | None:
        ...

    @abstractmethod
    async def save(self, account: Account) -> None:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...

    @abstractmethod
    async def save_token(self, token: str, username: str) -> None:
        ...

    @abstractmethod
    async def get_username_for_token(self, token: str) -> str | None:
        ...
