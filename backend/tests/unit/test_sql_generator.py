from types import SimpleNamespace

import pytest

from app.agent.agent import GeneratedSQL, SqlGenerator, FakeSqlGenerator, _extract_generated_sql
from app.agent.prompts import SYSTEM_PROMPT
from app.repositories.base import SchemaRepository, RelationshipInfo


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


class TestFormatSchema:
    @pytest.mark.asyncio
    async def test_format_schema_includes_relationships(self):
        from app.agent.tools import format_schema
        from app.repositories.memory.schema_repository_memory import InMemorySchemaRepository
        repo = InMemorySchemaRepository()
        output = await format_schema(repo)
        assert "orders" in output
        assert "customers" in output
        assert "customer_id" in output
        assert "->" in output


class TestExtractGeneratedSql:
    def test_prefers_output_attribute(self):
        generated = GeneratedSQL(sql="SELECT 1", explanation="ok")
        result = SimpleNamespace(output=generated)

        assert _extract_generated_sql(result) is generated

    def test_supports_legacy_data_attribute(self):
        generated = GeneratedSQL(sql="SELECT 1", explanation="ok")
        result = SimpleNamespace(data=generated)

        assert _extract_generated_sql(result) is generated

    def test_raises_when_result_shape_is_unexpected(self):
        with pytest.raises(AttributeError):
            _extract_generated_sql(SimpleNamespace())


class TestSystemPrompt:
    def test_prompt_includes_core_sql_guardrails(self):
        assert "Use only the tables, columns, and relationships shown in the schema tool." in SYSTEM_PROMPT
        assert "Never invent tables, columns, aliases, metrics, dimensions, or joins" in SYSTEM_PROMPT
        assert "Never generate write or admin SQL" in SYSTEM_PROMPT
        assert "Never query information_schema, pg_catalog, or any system tables." in SYSTEM_PROMPT

    def test_prompt_includes_clarification_guardrails(self):
        assert "If the question is ambiguous, under-specified, or impossible" in SYSTEM_PROMPT
        assert "Ask for clarification when the user requests data by a dimension that does not exist" in SYSTEM_PROMPT
