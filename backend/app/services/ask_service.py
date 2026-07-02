from app.domain.models import Answer, SqlQuery, ClarifyingQuestion
from app.repositories.base import SchemaRepository, QueryRepository
from app.agent.agent import SqlGenerator, GeneratedSQL
from app.guardrails.sql_validator import validate_sql
from app.core.config import settings


class AskService:
    def __init__(
        self,
        sql_generator: SqlGenerator,
        schema_repository: SchemaRepository,
        query_repository: QueryRepository,
    ):
        self._sql_generator = sql_generator
        self._schema_repo = schema_repository
        self._query_repo = query_repository

    async def answer(self, question: str) -> Answer | ClarifyingQuestion:
        generated = await self._sql_generator.generate(question)

        if generated.requires_clarification:
            return ClarifyingQuestion(
                question=generated.clarification_question or "What did you mean?",
                options=generated.clarification_options,
            )

        safe_sql, error = validate_sql(generated.sql, max_rows=settings.max_rows)
        if error:
            return Answer(text=f"I could not process that request: {error}")

        rows = await self._query_repo.execute(safe_sql)

        if not rows:
            return Answer(text="The query returned no results.", sql=SqlQuery(sql=generated.sql, explanation=generated.explanation))

        answer_text = _format_answer(rows, generated)

        return Answer(text=answer_text, sql=SqlQuery(sql=generated.sql, explanation=generated.explanation))


def _format_answer(rows: list[dict], generated: GeneratedSQL) -> str:
    if len(rows) == 1 and len(rows[0]) == 1:
        val = list(rows[0].values())[0]
        return f"The answer is **{val}**."

    count = len(rows)
    if count <= 5:
        lines = [f"- {dict(r)}" for r in rows]
        return f"Here are the results ({count} row(s)):\n" + "\n".join(lines)

    return f"Found **{count}** results. {generated.explanation}"
