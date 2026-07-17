import type { StepEvent } from '../api/askStreamApi'

interface StageConfig {
  stage: string
  label: string
  describe: (detail: Record<string, unknown>) => string
}

const STAGES: StageConfig[] = [
  {
    stage: 'planner',
    label: 'Planner',
    describe: (d) => {
      const score = typeof d.ambiguity_score === 'number' ? d.ambiguity_score : 0
      const unresolved = Array.isArray(d.unresolved_terms) ? d.unresolved_terms.length : 0
      return `Ambiguity ${(score * 100).toFixed(0)}% · ${unresolved} unresolved term(s)`
    },
  },
  {
    stage: 'sql_generator',
    label: 'SQL Generator',
    describe: (d) => (typeof d.explanation === 'string' && d.explanation ? d.explanation : 'Generating query'),
  },
  {
    stage: 'validator',
    label: 'Validator',
    describe: (d) => {
      const cost = typeof d.scan_cost === 'number' ? d.scan_cost : 0
      const deps = typeof d.dependency_count === 'number' ? d.dependency_count : 0
      return `Scan cost ${cost} · ${deps} dependenc(ies)`
    },
  },
  {
    stage: 'aggregator',
    label: 'Aggregator',
    describe: (d) => {
      const claims = typeof d.claims_count === 'number' ? d.claims_count : 0
      const headline = typeof d.headline === 'string' && d.headline ? ` — ${d.headline}` : ''
      return `${claims} claim(s) verified${headline}`
    },
  },
]

interface ThinkingTraceProps {
  steps: StepEvent[]
}

export function ThinkingTrace({ steps }: ThinkingTraceProps) {
  const byStage = new Map(steps.map((s) => [s.stage, s]))

  return (
    <div className="thinking-trace" data-testid="thinking-trace">
      {STAGES.map(({ stage, label, describe }) => {
        const completed = byStage.get(stage)
        return (
          <div key={stage} className={`thinking-trace-row ${completed ? 'done' : 'pending'}`}>
            <span className={`thinking-trace-icon ${completed ? 'check' : 'spinner'}`} aria-hidden="true" />
            <div className="thinking-trace-copy">
              <span className="thinking-trace-name">{label}</span>
              <span className="thinking-trace-detail">
                {completed ? describe(completed.detail) : 'Working…'}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
