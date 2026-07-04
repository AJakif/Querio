import pytest

from app.services.conversation_store import ConversationStore


class TestConversationStore:
    @pytest.fixture
    def store(self):
        return ConversationStore()

    def test_create_returns_conversation_id(self, store):
        conv_id = store.create("Show me customers", ["count", "list", "by region"])
        assert conv_id is not None
        assert len(conv_id) > 0

    def test_get_returns_context(self, store):
        conv_id = store.create("Show me customers", ["count", "list"])
        ctx = store.get(conv_id)
        assert ctx is not None
        assert ctx.original_question == "Show me customers"
        assert ctx.options == ["count", "list"]

    def test_get_returns_none_for_unknown_id(self, store):
        ctx = store.get("nonexistent")
        assert ctx is None

    def test_complete_removes_context(self, store):
        conv_id = store.create("Show me customers", ["count"])
        store.complete(conv_id)
        ctx = store.get(conv_id)
        assert ctx is None

    def test_create_generates_unique_ids(self, store):
        id1 = store.create("Question 1", ["a"])
        id2 = store.create("Question 2", ["b"])
        assert id1 != id2
