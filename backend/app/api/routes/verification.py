from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_account
from app.core.logging import get_logger
from app.domain.exceptions import QueryNotFoundError, SelfVerifyError
from app.domain.models import Account, Fingerprint, QueryRecord
from app.schemas.verification import (
    BadgeResponse,
    CheckDriftRequest,
    DisputeRequest,
    FingerprintIn,
    RegisterQueryRequest,
    VerifyRequest,
)
from app.services.verification_service import VerificationService

router = APIRouter()
logger = get_logger("api.verification")


def get_verification_service() -> VerificationService:
    from app.main import app_state

    if app_state is None:
        raise HTTPException(status_code=503, detail="Application not ready")
    return app_state.verification_service


def _to_domain_fingerprints(fps: list[FingerprintIn]) -> list[Fingerprint]:
    return [
        Fingerprint(
            table=fp.table,
            column=fp.column,
            schema_hash=fp.schema_hash,
            value_hash=fp.value_hash,
        )
        for fp in fps
    ]


def _badge_response(record: QueryRecord, drift_reasons: list[str] | None = None) -> BadgeResponse:
    last_verify = record.last_verification()
    return BadgeResponse(
        query_id=record.id,
        badge_state=record.badge_state().value,
        last_verifier=last_verify.actor if last_verify else None,
        last_verified_at=last_verify.timestamp.isoformat() if last_verify else None,
        drift_reasons=drift_reasons or [],
    )


@router.post("/queries", status_code=201)
async def register_query(
    body: RegisterQueryRequest,
    service: VerificationService = Depends(get_verification_service),
) -> BadgeResponse:
    query_id = str(uuid.uuid4())
    record = await service.register_query(
        query_id=query_id,
        sql=body.sql,
        author=body.author,
        question=body.question,
        fingerprints=_to_domain_fingerprints(body.fingerprints),
    )
    logger.info("Registered query record", extra={"query_id": query_id, "author": body.author})
    return _badge_response(record)


@router.get("/queries/{query_id}/badge")
async def get_badge(
    query_id: str,
    service: VerificationService = Depends(get_verification_service),
) -> BadgeResponse:
    try:
        record = await service.get_record(query_id)
    except QueryNotFoundError:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' not found.")
    return _badge_response(record)


@router.post("/queries/{query_id}/verify")
async def verify_query(
    query_id: str,
    body: VerifyRequest,
    account: Account = Depends(get_current_account),
    service: VerificationService = Depends(get_verification_service),
) -> BadgeResponse:
    try:
        record = await service.verify(
            query_id=query_id,
            verifier=account.username,
            fingerprints=_to_domain_fingerprints(body.fingerprints),
        )
    except QueryNotFoundError:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' not found.")
    except SelfVerifyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    logger.info("Query verified", extra={"query_id": query_id, "verifier": account.username})
    return _badge_response(record)


@router.post("/queries/{query_id}/dispute")
async def dispute_query(
    query_id: str,
    body: DisputeRequest,
    account: Account = Depends(get_current_account),
    service: VerificationService = Depends(get_verification_service),
) -> BadgeResponse:
    try:
        record = await service.dispute(query_id=query_id, actor=account.username)
    except QueryNotFoundError:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' not found.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    logger.info("Query disputed", extra={"query_id": query_id, "actor": account.username})
    return _badge_response(record)


@router.post("/queries/{query_id}/check-drift")
async def check_drift(
    query_id: str,
    body: CheckDriftRequest,
    service: VerificationService = Depends(get_verification_service),
) -> BadgeResponse:
    try:
        record, drift_reasons = await service.check_drift(
            query_id=query_id,
            current_fingerprints=_to_domain_fingerprints(body.current_fingerprints),
        )
    except QueryNotFoundError:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' not found.")
    logger.info(
        "Drift check complete",
        extra={"query_id": query_id, "drift_count": len(drift_reasons)},
    )
    return _badge_response(record, drift_reasons)
