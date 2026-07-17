"""Shared FastAPI dependencies for auth and service resolution."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.domain.models import Account
from app.services.account_service import AccountService


def get_account_service() -> AccountService:
    from app.main import app_state

    if app_state is None:
        raise HTTPException(status_code=503, detail="Application not ready")
    return app_state.account_service


async def get_current_account(
    authorization: str | None = Header(default=None),
    account_service: AccountService = Depends(get_account_service),
) -> Account:
    """Require a valid Bearer token; raise 401 with identity_required otherwise."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="identity_required")
    token = authorization.removeprefix("Bearer ")
    account = await account_service.get_account_for_token(token)
    if account is None:
        raise HTTPException(status_code=401, detail="identity_required")
    return account
