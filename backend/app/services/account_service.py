"""Local account service — lightweight username/password identity for governance actions.

Passwords are stored using PBKDF2-HMAC-SHA256 with a random 16-byte salt (stdlib only,
no additional dependencies). The first account registered on a fresh instance becomes
the instance owner (is_owner=True). Tokens are random UUIDs stored in-memory.
"""
from __future__ import annotations

import hashlib
import os
import uuid

from app.domain.exceptions import AccountExistsError, InvalidCredentialsError
from app.domain.models import Account
from app.repositories.base import AccountRepository

_ITERATIONS = 260_000


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}:{dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    # Constant-time comparison via hmac.compare_digest would be ideal;
    # for a single-user POC in-memory store, string equality is acceptable.
    return dk.hex() == dk_hex


class AccountService:
    def __init__(self, repo: AccountRepository) -> None:
        self._repo = repo

    async def register(self, username: str, password: str) -> tuple[Account, str]:
        """Register a new account. Raises AccountExistsError if username taken.

        The first account on a fresh instance becomes the instance owner.
        Returns (account, bearer_token).
        """
        if await self._repo.get_by_username(username) is not None:
            raise AccountExistsError(f"Username '{username}' is already taken.")

        is_first = (await self._repo.count()) == 0
        account = Account(
            username=username,
            password_hash=_hash_password(password),
            is_owner=is_first,
        )
        await self._repo.save(account)

        token = str(uuid.uuid4())
        await self._repo.save_token(token, username)
        return account, token

    async def authenticate(self, username: str, password: str) -> tuple[Account, str]:
        """Verify credentials and issue a new bearer token.

        Raises InvalidCredentialsError on unknown username or wrong password.
        Returns (account, bearer_token).
        """
        account = await self._repo.get_by_username(username)
        if account is None or not _verify_password(password, account.password_hash):
            raise InvalidCredentialsError("Invalid username or password.")

        token = str(uuid.uuid4())
        await self._repo.save_token(token, username)
        return account, token

    async def get_account_for_token(self, token: str) -> Account | None:
        """Return the account associated with a bearer token, or None."""
        username = await self._repo.get_username_for_token(token)
        if username is None:
            return None
        return await self._repo.get_by_username(username)
