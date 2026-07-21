import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AnswerCard } from './AnswerCard'
import type { AnswerSpec, ValidationResultResponse, TraceStep } from '../types/api'

const baseSpec: AnswerSpec = {
  headline: { value: '$13.6M', label: 'Net revenue', sign: 'neutral' },
  restatement: 'Net revenue for Q2 2024',
  chart_spec: null,
  suppression_reason: 'single-value; no chart needed',
  claims: [],
  followups: [],
  assumptions_ref: [
    { term: 'net revenue', resolution: 'payment_value minus refunds', alternatives: [], close_call: false },
    { term: 'Apr–Jun', resolution: 'Q2 calendar quarter', alternatives: [], close_call: false },
    { term: 'excludes cancelled', resolution: 'status != cancelled', alternatives: [], close_call: false },
  ],
  dropped_claim_count: 0,
}

const chartSpec = {
  chart_type: 'bar' as const,
  title: 'Revenue by Region',
  data: [
    { region: 'SP', revenue: 4200000 },
    { region: 'RJ', revenue: 1350000 },
  ],
  x_key: 'region',
  y_key: 'revenue',
  emphasis_target: 'SP',
}

const chartAnswerSpec: AnswerSpec = {
  response_type: 'chart',
  headline: { value: '$4.2M', label: 'SP Revenue', sign: 'positive' },
  restatement: 'Revenue in São Paulo for Q2 2024',
  chart_spec: chartSpec,
  suppression_reason: null,
  claims: [],
  followups: [],
  assumptions_ref: [
    { term: 'SP', resolution: 'São Paulo state only', alternatives: [], close_call: false },
  ],
  dropped_claim_count: 0,
}

describe('AnswerCard — chart route (ROUTE-2)', () => {
  it('renders chart-widget between headline and restatement for chart response_type', () => {
    const { container } = render(<AnswerCard spec={chartAnswerSpec} badge="verified" />)
    const card = container.querySelector('[data-testid="answer-card"]')!
    // Use deep querySelector + compareDocumentPosition — chart-widget is now wrapped in a
    // <div ref> for the PNG/SVG export path (slice 13) so it is no longer a direct child.
    const headline = card.querySelector('[data-testid="headline-stat"]')!
    const chart = card.querySelector('[data-testid="chart-widget"]')!
    const restatement = card.querySelector('[data-testid="answer-restatement"]')!
    // DOCUMENT_POSITION_FOLLOWING (4) means the argument node comes *after* the caller in document order
    expect(headline.compareDocumentPosition(chart) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
    expect(chart.compareDocumentPosition(restatement) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
  })
})

describe('AnswerCard — stat-only route', () => {
  it('renders badge before headline in DOM order', () => {
    const { container } = render(<AnswerCard spec={baseSpec} badge="unverified" />)
    const card = container.querySelector('[data-testid="answer-card"]')!
    const children = Array.from(card.children)
    const badgeIdx = children.findIndex((el) => el.getAttribute('data-testid') === 'badge-row')
    const headlineIdx = children.findIndex((el) => el.getAttribute('data-testid') === 'headline-stat')
    expect(badgeIdx).toBeGreaterThanOrEqual(0)
    expect(headlineIdx).toBeGreaterThan(badgeIdx)
  })

  it('renders Unverified badge with clock icon by default', () => {
    render(<AnswerCard spec={baseSpec} badge="unverified" />)
    const badge = screen.getByTestId('badge-row')
    expect(badge).toHaveClass('badge--unverified')
    expect(badge).toHaveTextContent('Unverified')
  })

  it('renders routine assumptions as a single compressed line (no amber chips)', () => {
    render(<AnswerCard spec={baseSpec} badge="unverified" />)
    const line = screen.getByTestId('assumption-line')
    // All assumptions are routine — no close-call chips
    expect(screen.queryByTestId('close-call-chip')).toBeNull()
    // Compressed text contains the terms
    expect(line).toHaveTextContent('net revenue')
    expect(line).toHaveTextContent('Apr–Jun')
    expect(line).toHaveTextContent('excludes cancelled')
  })

  it('breaks out a close-call assumption as an amber chip with its reason', () => {
    const specWithCloseCall: AnswerSpec = {
      ...baseSpec,
      assumptions_ref: [
        { term: 'net revenue', resolution: 'payment_value minus refunds', alternatives: [], close_call: false },
        {
          term: 'excludes cancelled',
          resolution: 'Cancelled orders are a large share (9%) — include them?',
          alternatives: ['include cancelled'],
          close_call: true,
        },
      ],
    }
    render(<AnswerCard spec={specWithCloseCall} badge="unverified" />)
    const chip = screen.getByTestId('close-call-chip')
    expect(chip).toHaveClass('assumption-chip--close-call')
    expect(chip).toHaveTextContent('excludes cancelled')
    expect(chip).toHaveTextContent('Cancelled orders are a large share')
    // Routine assumption still in compressed line
    expect(screen.getByTestId('assumption-line')).toHaveTextContent('net revenue')
  })

  it('renders no chart element for stat-only response type (ROUTE-1)', () => {
    const { container } = render(<AnswerCard spec={baseSpec} badge="unverified" />)
    // No chart widget, canvas, or recharts container
    expect(container.querySelector('.recharts-wrapper')).toBeNull()
    expect(container.querySelector('[data-testid="chart-widget"]')).toBeNull()
    expect(container.querySelector('canvas')).toBeNull()
  })

  it('renders empty-result answer as stat-only shape with assumption chips (ERR-3)', () => {
    const emptySpec: AnswerSpec = {
      ...baseSpec,
      headline: { value: '0', label: 'Net revenue (no matching orders)', sign: 'neutral' },
      claims: [],
    }
    render(<AnswerCard spec={emptySpec} badge="unverified" />)
    expect(screen.getByTestId('badge-row')).toBeInTheDocument()
    expect(screen.getByTestId('assumption-line')).toBeInTheDocument()
    const headline = screen.getByTestId('headline-stat')
    expect(headline).toHaveTextContent('0')
    expect(headline).toHaveTextContent('no matching orders')
  })
})

describe('AnswerCard — workbench drawer', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  const validation: ValidationResultResponse = {
    dependency_set: [{ table: 'fct_orders', column: 'payment_value' }],
    fingerprints: [
      { table: 'fct_orders', column: 'payment_value', schema_hash: 'abcdef1234567890', value_hash: null },
      { table: 'dim_customers', column: 'customer_state', schema_hash: 'deadbeef12345678', value_hash: 'cafe1234' },
    ],
    scan_cost: 99441,
  }

  const traceSteps: TraceStep[] = [
    { stage: 'planner', detail: { interpretation: 'net revenue Q2', ambiguity_score: '0.12' } },
    { stage: 'validator', detail: { rows_scanned: '99441' } },
  ]

  const sql = { sql: 'SELECT SUM(payment_value) FROM fct_orders', explanation: 'Summing payment values.' }

  const specWithFollowups: AnswerSpec = {
    ...baseSpec,
    followups: ['What drove the growth?', 'Break down by region', 'Compare to last quarter'],
  }

  it('workbench toggle is collapsed by default and expands on click', async () => {
    render(
      <AnswerCard spec={baseSpec} badge="unverified" sql={sql} validation={validation} traceSteps={traceSteps} />,
    )
    const toggle = screen.getByTestId('workbench-toggle')
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByTestId('workbench-drawer')).toBeNull()

    await userEvent.click(toggle)

    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByTestId('workbench-drawer')).toBeInTheDocument()
  })

  it('expanding workbench shows SQL, fingerprints, and trace content from fixture', async () => {
    render(
      <AnswerCard spec={baseSpec} badge="unverified" sql={sql} validation={validation} traceSteps={traceSteps} />,
    )
    await userEvent.click(screen.getByTestId('workbench-toggle'))

    // SQL
    expect(screen.getByTestId('workbench-sql')).toHaveTextContent('SELECT SUM(payment_value) FROM fct_orders')

    // Fingerprints
    const fp = screen.getByTestId('workbench-fingerprints')
    expect(fp).toHaveTextContent('fct_orders')
    expect(fp).toHaveTextContent('payment_value')
    expect(fp).toHaveTextContent('abcdef12') // first 8 chars of schema_hash

    // Trace stages
    const trace = screen.getByTestId('workbench-trace')
    expect(trace).toHaveTextContent('planner')
    expect(trace).toHaveTextContent('validator')

    // Cost estimate — check digit sequence without assuming locale comma
    expect(screen.getByTestId('workbench-cost').textContent).toMatch(/99.?441/)
  })

  it('shows chart-suppression reason in trace section when suppression_reason is set', async () => {
    render(
      <AnswerCard spec={baseSpec} badge="unverified" sql={sql} validation={validation} traceSteps={[]} />,
    )
    await userEvent.click(screen.getByTestId('workbench-toggle'))
    expect(screen.getByTestId('workbench-suppression')).toHaveTextContent('single-value; no chart needed')
  })

  it('follow-up chips render from spec.followups and call onSend on click', async () => {
    const onSend = vi.fn()
    render(<AnswerCard spec={specWithFollowups} badge="unverified" onSend={onSend} />)

    const strip = screen.getByTestId('followups-strip')
    expect(strip.querySelectorAll('.followup-chip')).toHaveLength(3)

    await userEvent.click(screen.getByText('What drove the growth?'))
    expect(onSend).toHaveBeenCalledWith('What drove the growth?')
  })

  it('stat-only export shows CSV only — PNG and SVG are hidden (BUG-3)', () => {
    // BUG-3 regression: stat answers have no SVG to rasterize, so PNG/SVG must not render.
    // CSV is always present; it uses resultRows (or falls back to empty) for the download.
    render(<AnswerCard spec={baseSpec} badge="unverified" />)
    const exportEl = screen.getByTestId('export-buttons')
    expect(exportEl).toHaveTextContent('CSV')
    expect(exportEl).not.toHaveTextContent('PNG')
    expect(exportEl).not.toHaveTextContent('SVG')
  })

  // REGRESSION Bug-4: restatement was nested inside the chart-only conditional,
  // so stat-only answers (single-value results) never rendered it.
  it('renders restatement text for stat-only answers (REGRESSION Bug-4)', () => {
    render(<AnswerCard spec={baseSpec} badge="unverified" />)
    // baseSpec has chart_spec=null → stat route; restatement must still appear
    expect(screen.getByTestId('answer-restatement')).toHaveTextContent('Net revenue for Q2 2024')
  })

  // REGRESSION Bug-7: BadgeRow never showed the verifier's name; it only rendered the
  // generic "Verified" label even when the backend supplied a verifier_name.
  it('renders "Verified by {name}" when badge is verified and verifierName is supplied (REGRESSION Bug-7)', () => {
    render(<AnswerCard spec={baseSpec} badge="verified" verifierName="carol" />)
    expect(screen.getByTestId('badge-row')).toHaveTextContent('Verified by carol')
  })
})
