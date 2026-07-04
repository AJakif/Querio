from app.domain.models import Answer, SqlQuery, ClarifyingQuestion
from app.repositories.base import SchemaRepository, QueryRepository
from app.agent.agent import SqlGenerator, GeneratedSQL
from app.guardrails.sql_validator import validate_sql
from app.services.conversation_store import ConversationStore
from app.core.config import settings


class AskService:
    def __init__(
        self,
        sql_generator: SqlGenerator,
        schema_repository: SchemaRepository,
        query_repository: QueryRepository,
        conversation_store: ConversationStore | None = None,
    ):
        self._sql_generator = sql_generator
        self._schema_repo = schema_repository
        self._query_repo = query_repository
        self._conversation_store = conversation_store or ConversationStore()

    async def answer(
        self,
        question: str,
        conversation_id: str | None = None,
        clarification_answer: str | None = None,
    ) -> Answer | ClarifyingQuestion:
        if conversation_id and clarification_answer is not None:
            ctx = self._conversation_store.get(conversation_id)
            if ctx is None:
                return Answer(text="Sorry, I couldn't find that conversation. Please try asking your question again.")
            self._conversation_store.complete(conversation_id)
            return await self._execute_answer(question, conversation_id)

        generated = await self._sql_generator.generate(question)

        if generated.requires_clarification:
            conv_id = self._conversation_store.create(question, generated.clarification_options)
            return ClarifyingQuestion(
                question=generated.clarification_question or "What did you mean?",
                options=generated.clarification_options,
                conversation_id=conv_id,
            )

        return await self._do_execute(generated, conversation_id)

    async def _do_execute(
        self, generated: GeneratedSQL, conversation_id: str | None = None
    ) -> Answer:
        safe_sql, error = validate_sql(generated.sql, max_rows=settings.max_rows)
        if error:
            return Answer(text=error, conversation_id=conversation_id)

        rows = await self._query_repo.execute(safe_sql)

        if not rows:
            return Answer(
                text="The query returned no results.",
                sql=SqlQuery(sql=generated.sql, explanation=generated.explanation),
                conversation_id=conversation_id,
            )

        answer_text = _format_answer(rows, generated)
        return Answer(
            text=answer_text,
            sql=SqlQuery(sql=generated.sql, explanation=generated.explanation),
            conversation_id=conversation_id,
        )

    async def _execute_answer(self, question: str, conversation_id: str) -> Answer:
        generated = await self._sql_generator.generate(question)
        return await self._do_execute(generated, conversation_id)


def _format_answer(rows: list[dict], generated: GeneratedSQL) -> str:
    if len(rows) == 1 and len(rows[0]) == 1:
        val = list(rows[0].values())[0]
        return f"The answer is **{val}**."

    count = len(rows)
    if count <= 5:
        lines = [f"- {dict(r)}" for r in rows]
        return f"Here are the results ({count} row(s)):\n" + "\n".join(lines)

    return f"Found **{count}** results. {generated.explanation}"
