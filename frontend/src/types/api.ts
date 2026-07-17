export interface AskRequest {
  question: string
  conversation_id?: string
  clarification_answer?: string
}

export interface ChartSpecResponse {
  chart_type: 'bar' | 'line' | 'histogram'
  title: string
  data: Record<string, unknown>[]
  x_key: string
  y_key: string
}

export interface SqlQueryResponse {
  sql: string
  explanation: string
}

export interface AnswerResponse {
  type: 'answer'
  answer: string
  chart: ChartSpecResponse | null
  sql: SqlQueryResponse | null
  conversation_id: string | null
}

export interface ClarifyingQuestionResponse {
  type: 'clarifying_question'
  question: string
  options: string[]
  conversation_id: string
}

export type AskResponse = AnswerResponse | ClarifyingQuestionResponse

export interface UserMessage {
  type: 'user'
  question: string
}

export type ChatMessage = AskResponse | UserMessage

export interface ExampleQuestionResponse {
  question: string
  answer_shape: 'number' | 'chart' | 'list'
  hint: string
}

export interface SchemaSummaryResponse {
  table_name: string
  row_count: number
  date_span_start: string | null
  date_span_end: string | null
  key_dimension_count: number
  headline_label: string
  headline_value: number
  examples: ExampleQuestionResponse[]
}
