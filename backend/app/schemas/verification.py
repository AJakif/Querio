from __future__ import annotations

from pydantic import BaseModel


class FingerprintIn(BaseModel):
    table: str
    column: str
    schema_hash: str
    value_hash: str | None = None


class RegisterQueryRequest(BaseModel):
    sql: str
    author: str
    question: str = ""
    fingerprints: list[FingerprintIn] = []


class VerifyRequest(BaseModel):
    # identity comes from Bearer token; verifier is resolved server-side
    fingerprints: list[FingerprintIn] = []


class DisputeRequest(BaseModel):
    # identity comes from Bearer token; actor is resolved server-side
    pass


class CheckDriftRequest(BaseModel):
    current_fingerprints: list[FingerprintIn] = []


class BadgeResponse(BaseModel):
    query_id: str
    badge_state: str
    last_verifier: str | None = None
    last_verified_at: str | None = None
    drift_reasons: list[str] = []
