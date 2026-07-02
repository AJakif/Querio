from abc import ABC, abstractmethod

from pydantic import BaseModel
from pydantic_ai import Agent as PydanticAgent

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import get_schema
from app.repositories.base import SchemaRepository


class GeneratedSQL(BaseModel):
    sql: str
    explanation: str
    requires_clarification: bool = False
    clarification_question: str = ""
    clarification_options: list[str] = []


class SqlGenerator(ABC):
    @abstractmethod
    async def generate(self, question: str) -> GeneratedSQL:
        ...


class PydanticAiSqlGenerator(SqlGenerator):
    def __init__(self, model_name: str, schema_repo: SchemaRepository):
        self._agent = PydanticAgent(
            model_name,
            system_prompt=SYSTEM_PROMPT,
            result_type=GeneratedSQL,
        )
        self._agent.tool(get_schema)
        self._schema_repo = schema_repo

    async def generate(self, question: str) -> GeneratedSQL:
        result = await self._agent.run(question, deps=self._schema_repo)
        return result.data


class FakeSqlGenerator(SqlGenerator):
    async def generate(self, question: str) -> GeneratedSQL:
        return GeneratedSQL(
            sql="SELECT COUNT(*) AS order_count FROM orders",
            explanation="Counting all orders in the database.",
        )
