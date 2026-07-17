"""Verified-query lifecycle service.

Badge state is COMPUTED from an append-only VerificationEvent history — never stored
as a mutable field. Drift detection compares fingerprints at run-time against those
recorded at the last verification event.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.domain.exceptions import QueryNotFoundError, SelfVerifyError
from app.domain.models import (
    BadgeState,
    Fingerprint,
    QueryRecord,
    VerificationEvent,
    VerificationEventType,
)
from app.repositories.base import QueryRecordRepository


class VerificationService:
    def __init__(self, repo: QueryRecordRepository) -> None:
        self._repo = repo

    async def register_query(
        self,
        query_id: str,
        sql: str,
        author: str,
        fingerprints: list[Fingerprint],
        question: str = "",
    ) -> QueryRecord:
        """Create a new QueryRecord in Unverified state."""
        record = QueryRecord(
            id=query_id,
            sql=sql,
            author=author,
            question=question,
            fingerprints_at_run=fingerprints,
        )
        await self._repo.save(record)
        return record

    async def find_verified_by_question(self, normalized_question: str) -> QueryRecord | None:
        """Return the first Verified record whose question matches the normalized form, or None.

        Badge state is computed live — never trusts a cached flag.
        Any state other than clean Verified returns None so the caller falls through to
        the full pipeline (hard correctness rule: stale answers must never be re-served).
        """
        records = await self._repo.list_all()
        for record in records:
            if _normalize_question(record.question) == normalized_question:
                if record.badge_state() == BadgeState.verified:
                    return record
        return None

    async def verify(
        self,
        query_id: str,
        verifier: str,
        fingerprints: list[Fingerprint],
    ) -> QueryRecord:
        """Move query to Verified. Raises SelfVerifyError if verifier == author.

        Records verifier + timestamp + fingerprints at verification time.
        Re-verification after Needs recheck or Disputed restores Verified.
        """
        record = await self._get_or_raise(query_id)

        if verifier == record.author:
            raise SelfVerifyError(
                f"Author '{verifier}' cannot verify their own query."
            )

        record.history.append(
            VerificationEvent(
                event_type=VerificationEventType.verified,
                actor=verifier,
                timestamp=datetime.now(tz=timezone.utc),
                fingerprints=fingerprints,
            )
        )
        await self._repo.save(record)
        return record

    async def dispute(self, query_id: str, actor: str) -> QueryRecord:
        """Flag a Verified query as Disputed. Disputed outranks Verified until re-verification."""
        record = await self._get_or_raise(query_id)
        current_state = record.badge_state()

        if current_state != BadgeState.verified:
            raise ValueError(
                f"Cannot dispute a query in state '{current_state.value}'. "
                "Only Verified queries can be disputed."
            )

        record.history.append(
            VerificationEvent(
                event_type=VerificationEventType.disputed,
                actor=actor,
                timestamp=datetime.now(tz=timezone.utc),
            )
        )
        await self._repo.save(record)
        return record

    async def check_drift(
        self,
        query_id: str,
        current_fingerprints: list[Fingerprint],
    ) -> tuple[QueryRecord, list[str]]:
        """Compare current fingerprints against those at last verification.

        If any structural (schema_hash) or semantic (value_hash) drift is detected,
        appends a needs_recheck event naming each change.

        Returns (record, drift_reasons). drift_reasons is empty when no drift.
        """
        record = await self._get_or_raise(query_id)

        # Only a Verified query can drift to Needs recheck.
        if record.badge_state() != BadgeState.verified:
            return record, []

        last_verify = record.last_verification()
        if last_verify is None:
            return record, []

        drift_reasons = _detect_drift(last_verify.fingerprints, current_fingerprints)
        if not drift_reasons:
            return record, []

        record.history.append(
            VerificationEvent(
                event_type=VerificationEventType.needs_recheck,
                actor="system",
                timestamp=datetime.now(tz=timezone.utc),
                drift_reason="; ".join(drift_reasons),
            )
        )
        await self._repo.save(record)
        return record, drift_reasons

    async def get_record(self, query_id: str) -> QueryRecord:
        return await self._get_or_raise(query_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _get_or_raise(self, query_id: str) -> QueryRecord:
        record = await self._repo.get(query_id)
        if record is None:
            raise QueryNotFoundError(f"Query '{query_id}' not found.")
        return record


def _normalize_question(text: str) -> str:
    """Canonical form for question matching: strip whitespace, lowercase."""
    return text.strip().lower()


def _detect_drift(
    verified: list[Fingerprint],
    current: list[Fingerprint],
) -> list[str]:
    """Return human-readable drift descriptions for each changed fingerprint.

    Structural drift: schema_hash changed (column renamed, type changed, etc.).
    Semantic drift: value_hash changed (new distinct value appeared in filter column).
    """
    verified_map: dict[tuple[str, str], Fingerprint] = {
        (fp.table, fp.column): fp for fp in verified
    }
    reasons: list[str] = []

    for fp in current:
        key = (fp.table, fp.column)
        baseline = verified_map.get(key)
        if baseline is None:
            continue  # new dependency added — not treated as drift on its own

        if fp.schema_hash != baseline.schema_hash:
            reasons.append(f"{fp.table}.{fp.column} schema changed")

        if (
            fp.value_hash is not None
            and baseline.value_hash is not None
            and fp.value_hash != baseline.value_hash
        ):
            reasons.append(f"{fp.table}.{fp.column} has a new value")

    return reasons
