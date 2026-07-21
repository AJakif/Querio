import type { StepEvent } from '../api/askStreamApi'

const FROM_REGEX = /\bFROM\s+([\w."'`[\]]+)/i

function extractTableName(sql: string): string | null {
  const match = FROM_REGEX.exec(sql)
  if (!match || !match[1]) return null
  const identifier = match[1].replace(/["'`[\]]/g, '')
  const parts = identifier.split('.')
  return parts[parts.length - 1] ?? null
}

export function getPipelinePhrase(steps: StepEvent[]): string {
  const stages = new Set(steps.map((s) => s.stage))

  if (stages.has('aggregator')) return 'Checking the numbers…'
  if (stages.has('validator')) return 'Running the query…'

  if (stages.has('sql_generator')) {
    const sqlStep = steps.find((s) => s.stage === 'sql_generator')
    const sql = typeof sqlStep?.detail?.sql === 'string' ? sqlStep.detail.sql : ''
    const table = sql ? extractTableName(sql) : null
    return table ? `Looking at your ${table} table…` : 'Looking at your data…'
  }

  if (stages.has('planner')) return 'Looking at your data…'

  return 'Understanding your question…'
}

export function PipelineStatus({ steps }: { steps: StepEvent[] }) {
  const phrase = getPipelinePhrase(steps)
  return (
    <div className="pipeline-status" data-testid="pipeline-status">
      <span className="pipeline-status-dot" aria-hidden="true" />
      <span className="pipeline-status-text">{phrase}</span>
    </div>
  )
}
