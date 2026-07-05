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
