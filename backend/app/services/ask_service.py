from app.domain.models import Answer, ChartSpec, ChartType, SqlQuery, ClarifyingQuestion
from app.repositories.base import SchemaRepository, QueryRepository


class AskService:
    def __init__(
        self,
        schema_repository: SchemaRepository,
        query_repository: QueryRepository,
    ):
        self._schema_repo = schema_repository
        self._query_repo = query_repository

    async def answer(self, question: str) -> Answer | ClarifyingQuestion:
        return Answer(
            text=f"There are 100 orders in the database.",
            chart=ChartSpec(
                chart_type=ChartType.bar,
                title="Orders Overview",
                data=[{"month": "Jan", "count": 30}, {"month": "Feb", "count": 40}, {"month": "Mar", "count": 30}],
                x_key="month",
                y_key="count",
            ),
            sql=SqlQuery(
                sql="SELECT date_trunc('month', order_date) AS month, COUNT(*) AS count FROM orders GROUP BY month",
                explanation="Count of orders grouped by month",
            ),
        )
