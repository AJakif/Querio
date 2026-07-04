import uuid
from dataclasses import dataclass


@dataclass
class ConversationContext:
    original_question: str
    options: list[str]


class ConversationStore:
    def __init__(self):
        self._store: dict[str, ConversationContext] = {}

    def create(self, original_question: str, options: list[str]) -> str:
        conv_id = str(uuid.uuid4())
        self._store[conv_id] = ConversationContext(
            original_question=original_question,
            options=options,
        )
        return conv_id

    def get(self, conversation_id: str) -> ConversationContext | None:
        return self._store.get(conversation_id)

    def complete(self, conversation_id: str) -> None:
        self._store.pop(conversation_id, None)
