import { useEffect, useState } from 'react'
import { fetchSchemaSummary } from '../api/schemaApi'
import type { SchemaSummaryResponse } from '../types/api'

interface EmptyStateEdaProps {
  sessionId?: string
  onSend: (question: string) => void
}

function formatDateSpan(summary: SchemaSummaryResponse): string | null {
  if (!summary.date_span_start || !summary.date_span_end) return null
  return `${summary.date_span_start} to ${summary.date_span_end}`
}

function formatHeadline(summary: SchemaSummaryResponse): string {
  const value = summary.headline_value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  return `${summary.headline_label}: ${value}`
}

export function EmptyStateEda({ sessionId, onSend }: EmptyStateEdaProps) {
  const [summary, setSummary] = useState<SchemaSummaryResponse | null>(null)
  const [error, setError] = useState<string | undefined>()

  useEffect(() => {
    let cancelled = false
    setSummary(null)
    setError(undefined)

    fetchSchemaSummary(sessionId)
      .then((data) => {
        if (!cancelled) setSummary(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load dataset summary')
      })

    return () => {
      cancelled = true
    }
  }, [sessionId])

  if (error) {
    return <div className="empty-state-eda empty-state-eda-error">{error}</div>
  }

  if (!summary) {
    return <div className="empty-state-eda empty-state-eda-loading">Loading dataset summary...</div>
  }

  const dateSpan = formatDateSpan(summary)

  return (
    <div className="empty-state-eda">
      <div className="eda-strip">
        <span className="eda-stat">{summary.row_count.toLocaleString()} rows</span>
        {dateSpan && <span className="eda-stat">{dateSpan}</span>}
        <span className="eda-stat">{summary.key_dimension_count} key dimensions</span>
        <span className="eda-stat eda-headline">{formatHeadline(summary)}</span>
      </div>
      <div className="eda-examples">
        {summary.examples.map((example) => (
          <button
            key={example.question}
            type="button"
            className="eda-example-question"
            onClick={() => onSend(example.question)}
          >
            <span className="eda-example-text">{example.question}</span>
            <span className="eda-example-hint">{example.hint}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
