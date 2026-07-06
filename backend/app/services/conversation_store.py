import uuid
from dataclasses import dataclass

from app.core.logging import get_logger


logger = get_logger("conversation_store")


@dataclass
class ConversationContext:
    original_question: str
    options: list[str]


class ConversationStore:
    def __init__(self):
        self._store: dict[str, ConversationContext] = {}
        logger.debug("Conversation store initialized")

    def create(self, original_question: str, options: list[str]) -> str:
        conv_id = str(uuid.uuid4())
        self._store[conv_id] = ConversationContext(
            original_question=original_question,
            options=options,
        )
        logger.debug(
            "Conversation created",
            extra={"conversation_id": conv_id, "options_count": len(options)},
        )
        return conv_id

    def get(self, conversation_id: str) -> ConversationContext | None:
        context = self._store.get(conversation_id)
        logger.debug(
            "Conversation lookup",
            extra={"conversation_id": conversation_id, "found": context is not None},
        )
        return context

    def complete(self, conversation_id: str) -> None:
        removed = self._store.pop(conversation_id, None)
        logger.debug(
            "Conversation completed",
            extra={"conversation_id": conversation_id, "found": removed is not None},
        )
