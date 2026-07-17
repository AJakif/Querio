from pydantic import BaseModel


class ExampleQuestionResponse(BaseModel):
    question: str
    answer_shape: str
    hint: str


class SchemaSummaryResponse(BaseModel):
    table_name: str
    row_count: int
    date_span_start: str | None
    date_span_end: str | None
    key_dimension_count: int
    headline_label: str
    headline_value: float
    examples: list[ExampleQuestionResponse]
