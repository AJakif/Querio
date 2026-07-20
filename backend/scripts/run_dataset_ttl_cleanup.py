"""Run the dataset TTL cleanup job.

Usage:
    python scripts/run_dataset_ttl_cleanup.py

Reads DATABASE_URL and DATASET_TTL_DAYS from the environment.
Safe to run multiple times — already-expired sessions are idempotent.
"""

from __future__ import annotations

import asyncio


async def _main() -> None:
    from app.core.config import settings
    from app.repositories.postgres.chat_history_repository_pg import (
        PostgresChatHistoryRepository,
    )
    from app.services.dataset_ttl_service import DatasetTTLService
    from app.services.session_manager import SessionManager

    repo = PostgresChatHistoryRepository()
    session_manager = SessionManager()
    service = DatasetTTLService(chat_history_repo=repo, session_manager=session_manager)

    ttl_days = settings.dataset_ttl_days
    print(f"[dataset-ttl] Running cleanup with TTL={ttl_days} days")

    cleaned = await service.run_cleanup(ttl_days=ttl_days)

    if cleaned:
        print(f"[dataset-ttl] Expired {len(cleaned)} session(s): {cleaned}")
    else:
        print("[dataset-ttl] No sessions eligible for cleanup")


if __name__ == "__main__":
    asyncio.run(_main())
