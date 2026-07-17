import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.agent.contracts import PlanResult
    from app.repositories.base import SchemaRepository, QueryRepository


logger = get_logger("confirm_store")


@dataclass
class ConfirmPendingState:
    original_question: str
    plan_result: "PlanResult"
    schema_repo: "SchemaRepository | None"
    query_repo: "QueryRepository | None"
    gate_reason: str  # "ambiguity" | "cost"


class ConfirmStore:
    def __init__(self) -> None:
        self._store: dict[str, ConfirmPendingState] = {}
        logger.debug("ConfirmStore initialized")

    def create(self, state: ConfirmPendingState) -> str:
        confirm_id = str(uuid.uuid4())
        self._store[confirm_id] = state
        logger.debug(
            "Confirm state created",
            extra={"confirm_id": confirm_id, "gate_reason": state.gate_reason},
        )
        return confirm_id

    def get(self, confirm_id: str) -> ConfirmPendingState | None:
        return self._store.get(confirm_id)

    def complete(self, confirm_id: str) -> None:
        self._store.pop(confirm_id, None)
        logger.debug("Confirm state completed", extra={"confirm_id": confirm_id})
