import pytest

from app.agent.agent import GeneratedSQL, SqlGenerator, FakeSqlGenerator


class TestGeneratedSQL:
    def test_default_requires_clarification_is_false(self):
        g = GeneratedSQL(sql="SELECT 1", explanation="test")
        assert g.sql == "SELECT 1"
        assert g.explanation == "test"
        assert g.requires_clarification is False
        assert g.clarification_options == []

    def test_can_set_clarification(self):
        g = GeneratedSQL(
            sql="", explanation="unclear",
            requires_clarification=True,
            clarification_question="Which table?",
            clarification_options=["orders", "customers"],
        )
        assert g.requires_clarification is True
        assert "orders" in g.clarification_options


class TestSqlGenerator:
    def test_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            SqlGenerator()


class TestFakeSqlGenerator:
    @pytest.mark.asyncio
    async def test_generate_returns_canned_sql(self):
        gen = FakeSqlGenerator()
        result = await gen.generate("How many orders?")
        assert isinstance(result, GeneratedSQL)
        assert "COUNT" in result.sql.upper() or "SELECT" in result.sql.upper()
        assert result.requires_clarification is False
