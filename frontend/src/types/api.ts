export interface AskRequest {
  question: string
  conversation_id?: string
  clarification_answer?: string
}

export interface AssumptionResponse {
  term: string
  resolution: string
  alternatives: string[]
  close_call: boolean
}

export interface PlanResponse {
  ambiguity_score: number
  assumptions: AssumptionResponse[]
  unresolved_terms: string[]
  interpretation: string
}

export interface ConfirmFirstResponse {
  type: 'confirm_first'
  conversation_id: string
  plan: PlanResponse
  scan_cost: number
  gate_reason: 'ambiguity' | 'cost'
}

export interface FingerprintResponse {
  table: string
  column: string
  schema_hash: string
  value_hash: string | null
}

export interface ValidationResultResponse {
  dependency_set: { table: string; column: string }[]
  fingerprints: FingerprintResponse[]
  scan_cost: number
}

/** Client-side-only: accumulated SSE trace steps stored on the answer after streaming completes. */
export interface TraceStep {
  stage: string
  detail: Record<string, unknown>
}

export interface ChartSpecResponse {
  chart_type: 'stat' | 'line' | 'bar' | 'histogram' | 'emphasis' | 'diverging_bar' | 'stacked_bar'
  title: string
  data: Record<string, unknown>[]
  x_key: string
  y_key: string
  /** For stacked_bar: ordered list of series keys stacked on each bar */
  y_keys?: string[] | null
  /** Category value (x_key) of the mark the lead claim is about; renders full-saturation */
  emphasis_target?: string | null
}

export interface SqlQueryResponse {
  sql: string
  explanation: string
}

// AnswerSpec types — mirror backend/app/agent/contracts.py
export interface Assumption {
  term: string
  resolution: string
  alternatives: string[]
  close_call: boolean
}

export interface Headline {
  value: string
  label: string
  sign: 'positive' | 'negative' | 'neutral'
}

export interface Claim {
  sentence: string
  type: 'row' | 'computation'
  cells: Record<string, unknown>[]
  operation?: string | null
  operands?: number[] | null
  value?: number | null
}

export interface AnswerSpec {
  /** Routing key: 'stat' suppresses chart; 'chart' renders ChartWidget between headline and summary */
  response_type?: 'stat' | 'chart' | null
  headline: Headline
  restatement: string
  chart_spec?: ChartSpecResponse | null
  suppression_reason?: string | null
  claims: Claim[]
  followups: string[]
  assumptions_ref: Assumption[]
  dropped_claim_count: number
}

// BadgeState — mirrors backend/app/domain/models.py BadgeState enum
export type BadgeState = 'unverified' | 'verified' | 'needs_recheck' | 'disputed'

export interface AnswerResponse {
  type: 'answer'
  answer: string
  chart: ChartSpecResponse | null
  sql: SqlQueryResponse | null
  conversation_id: string | null
  answer_spec?: AnswerSpec | null
  badge_state?: BadgeState | null
  verifier_name?: string | null
  query_id?: string | null
  validation?: ValidationResultResponse | null
  /** Raw query result rows — used for CSV export regardless of response_type. */
  result_rows?: Record<string, unknown>[] | null
  /** Client-only: SSE trace steps captured during streaming. Not from the server. */
  _trace_steps?: TraceStep[]
}

export interface ClarifyingQuestionResponse {
  type: 'clarifying_question'
  question: string
  options: string[]
  conversation_id: string
}

export interface ProxyAlternative {
  label: string
  question: string
}

export interface ClarifyResponse {
  type: 'clarify'
  statement: string
  unresolved_terms: string[]
  alternatives: ProxyAlternative[]
  add_data: boolean
  conversation_id?: string | null
}

export type AskResponse = AnswerResponse | ClarifyingQuestionResponse | ClarifyResponse | ConfirmFirstResponse

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
