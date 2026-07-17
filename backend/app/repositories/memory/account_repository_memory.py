from __future__ import annotations

from app.domain.models import Account
from app.repositories.base import AccountRepository


class InMemoryAccountRepository(AccountRepository):
    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}  # username → Account
        self._tokens: dict[str, str] = {}  # token → username

    async def get_by_username(self, username: str) -> Account | None:
        return self._accounts.get(username)

    async def save(self, account: Account) -> None:
        self._accounts[account.username] = account

    async def count(self) -> int:
        return len(self._accounts)

    async def save_token(self, token: str, username: str) -> None:
        self._tokens[token] = username

    async def get_username_for_token(self, token: str) -> str | None:
        return self._tokens.get(token)
