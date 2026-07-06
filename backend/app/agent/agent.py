from abc import ABC, abstractmethod

from pydantic import BaseModel
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.logging import get_logger
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import get_schema
from app.repositories.base import SchemaRepository

logger = get_logger("agent")


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


def _build_model(model_name: str, openai_api_key: str | None, anthropic_api_key: str | None):
    provider_name, separator, provider_model = model_name.partition(":")
    if not separator:
        logger.debug("Using raw model name without provider adapter", extra={"model_name": model_name})
        return model_name

    if provider_name == "openai" and openai_api_key:
        logger.debug("Building OpenAI model adapter", extra={"model_name": provider_model})
        return OpenAIChatModel(
            provider_model,
            provider=OpenAIProvider(api_key=openai_api_key),
        )

    if provider_name == "anthropic" and anthropic_api_key:
        logger.debug("Building Anthropic model adapter", extra={"model_name": provider_model})
        return AnthropicModel(
            provider_model,
            provider=AnthropicProvider(api_key=anthropic_api_key),
        )

    logger.warning(
        "Falling back to unresolved model name",
        extra={"model_name": model_name, "provider_name": provider_name},
    )
    return model_name


class PydanticAiSqlGenerator(SqlGenerator):
    def __init__(
        self,
        model_name: str,
        schema_repo: SchemaRepository,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
    ):
        logger.info("Initializing Pydantic AI SQL generator", extra={"model_name": model_name})
        self._agent = PydanticAgent(
            _build_model(model_name, openai_api_key, anthropic_api_key),
            system_prompt=SYSTEM_PROMPT,
            output_type=GeneratedSQL,
            deps_type=SchemaRepository,
        )
        self._agent.tool(get_schema)
        self._schema_repo = schema_repo

    async def generate(self, question: str) -> GeneratedSQL:
        logger.debug("Generating SQL from model", extra={"question_length": len(question)})
        result = await self._agent.run(question, deps=self._schema_repo)
        logger.debug(
            "Model returned SQL result",
            extra={
                "requires_clarification": result.data.requires_clarification,
                "sql_preview": result.data.sql[:120],
            },
        )
        return result.data


class FakeSqlGenerator(SqlGenerator):
    async def generate(self, question: str) -> GeneratedSQL:
        logger.debug("Using fake SQL generator", extra={"question_length": len(question)})
        return GeneratedSQL(
            sql="SELECT COUNT(*) AS order_count FROM marts.fct_orders",
            explanation="Counting all orders in the marts fact table.",
        )
