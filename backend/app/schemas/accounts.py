from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    username: str
    password: str


class AccountResponse(BaseModel):
    username: str
    is_owner: bool
    token: str
