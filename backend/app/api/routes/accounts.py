from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_account_service
from app.domain.exceptions import AccountExistsError, InvalidCredentialsError
from app.schemas.accounts import AccountResponse, LoginRequest, RegisterRequest
from app.services.account_service import AccountService

router = APIRouter()


@router.post("/accounts", status_code=201)
async def register(
    body: RegisterRequest,
    service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Register a new local account. The first account becomes the instance owner."""
    try:
        account, token = await service.register(body.username, body.password)
    except AccountExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return AccountResponse(username=account.username, is_owner=account.is_owner, token=token)


@router.post("/accounts/login")
async def login(
    body: LoginRequest,
    service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Authenticate and receive a bearer token."""
    try:
        account, token = await service.authenticate(body.username, body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return AccountResponse(username=account.username, is_owner=account.is_owner, token=token)
