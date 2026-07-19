from abc import ABC, abstractmethod

from pydantic_ai import Agent as PydanticAgent

from app.agent.agent import _build_model
from app.agent.contracts import PlanResult
from app.agent.prompt_builder import build_dynamic_state, build_static_prefix
from app.agent.prompts import PLANNER_INSTRUCTIONS
from app.agent.tools import get_schema
from app.core.logging import get_logger
from app.repositories.base import SchemaRepository


logger = get_logger("agent.planner")


class Planner(ABC):
    @abstractmethod
    async def plan(
        self,
        question: str,
        schema_repo_override: SchemaRepository | None = None,
    ) -> PlanResult:
        ...


class PydanticAiPlanner(Planner):
    def __init__(
        self,
        model_name: str,
        schema_repo: SchemaRepository,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        ollama_base_url: str | None = None,
        ollama_num_ctx: int | None = None,
    ):
        logger.info("Initializing Pydantic AI planner", extra={"model_name": model_name})
        self._system_prompt = build_static_prefix() + "\n\n" + PLANNER_INSTRUCTIONS
        self._agent = PydanticAgent(
            _build_model(model_name, openai_api_key, anthropic_api_key, ollama_base_url, ollama_num_ctx),
            system_prompt=self._system_prompt,
            output_type=PlanResult,
            deps_type=SchemaRepository,
        )
        self._agent.tool(get_schema)
        self._schema_repo = schema_repo

    async def plan(
        self,
        question: str,
        schema_repo_override: SchemaRepository | None = None,
    ) -> PlanResult:
        repo = schema_repo_override or self._schema_repo
        logger.debug("Running planner", extra={"question_length": len(question)})
        result = await self._agent.run(
            build_dynamic_state(session_brief="", question=question),
            deps=repo,
        )
        output = getattr(result, "output", None) or getattr(result, "data", None)
        if output is None:
            raise AttributeError("Planner AgentRunResult contained no 'output' or 'data'.")
        logger.debug(
            "Planner result",
            extra={
                "ambiguity_score": output.ambiguity_score,
                "assumption_count": len(output.assumptions),
                "unresolved_count": len(output.unresolved_terms),
            },
        )
        return output


class FakePlanner(Planner):
    """Deterministic fallback used when no LLM API key is configured."""

    async def plan(
        self,
        question: str,
        schema_repo_override: SchemaRepository | None = None,
    ) -> PlanResult:
        logger.debug("Using fake planner", extra={"question_length": len(question)})
        return PlanResult(
            ambiguity_score=0.0,
            assumptions=[],
            unresolved_terms=[],
            interpretation=question,
        )
