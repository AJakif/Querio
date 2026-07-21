import type { AnswerResponse } from '../types/api'
import { ChartWidget } from './charts/ChartWidget'
import { AnswerCard } from './AnswerCard'

interface ResultsPaneProps {
  message: AnswerResponse | null
  onSend?: (question: string) => void
}

/**
 * Right-hand pane — shows the chart/table/SQL/workbench detail for whichever
 * turn is currently selected in the chat pane. The chat pane only ever shows
 * a short teaser; this is where "everything else" lives.
 */
export function ResultsPane({ message, onSend }: ResultsPaneProps) {
  if (!message) {
    return (
      <div className="results-pane-empty" data-testid="results-pane-empty">
        <p>Ask a question to see charts, tables, and query details here.</p>
      </div>
    )
  }

  if (message.answer_spec) {
    return (
      <AnswerCard
        spec={message.answer_spec}
        badge={message.badge_state ?? 'unverified'}
        onSend={onSend}
        sql={message.sql}
        validation={message.validation}
        traceSteps={message._trace_steps}
        resultRows={message.result_rows}
      />
    )
  }

  // Legacy path: the answer text itself already lives in the chat-pane teaser
  // (there's no separate headline/detail split for this shape) — this pane
  // only adds the chart and SQL, i.e. exactly the parts not shown there.
  if (!message.chart && !message.sql) {
    return (
      <div className="results-pane-empty" data-testid="results-pane-empty">
        <p>No chart or query detail for this turn.</p>
      </div>
    )
  }

  return (
    <div className="results-pane-legacy" data-testid="results-pane-legacy">
      {message.chart && (
        <div className="chart-container">
          <ChartWidget chart={message.chart} />
        </div>
      )}
      {message.sql && (
        <details className="sql-details" open>
          <summary>SQL</summary>
          <pre><code>{message.sql.sql}</code></pre>
          <p className="sql-explanation">{message.sql.explanation}</p>
        </details>
      )}
    </div>
  )
}
