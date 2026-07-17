import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChartWidget, emphasisFill } from './ChartWidget'
import type { ChartSpecResponse } from '../../types/api'

// ---------------------------------------------------------------------------
// Shared fixture builders
// ---------------------------------------------------------------------------

const regionData = [
  { region: 'SP', revenue: 4200000 },
  { region: 'RJ', revenue: 1350000 },
  { region: 'MG', revenue: 1100000 },
]

function makeSpec(
  chart_type: ChartSpecResponse['chart_type'],
  overrides: Partial<ChartSpecResponse> = {},
): ChartSpecResponse {
  return {
    chart_type,
    title: `Test ${chart_type}`,
    data: regionData,
    x_key: 'region',
    y_key: 'revenue',
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Form render tests — one per dispatch path, asserts chart-widget mounts
// ---------------------------------------------------------------------------

describe('ChartWidget — form renders', () => {
  const forms: ChartSpecResponse['chart_type'][] = [
    'bar',
    'line',
    'histogram',
    'emphasis',
    'diverging_bar',
    'stacked_bar',
  ]

  for (const form of forms) {
    it(`renders chart-widget container for form: ${form}`, () => {
      const spec =
        form === 'stacked_bar'
          ? makeSpec(form, { y_keys: ['revenue', 'refunds'] })
          : makeSpec(form)
      render(<ChartWidget chart={spec} />)
      expect(screen.getByTestId('chart-widget')).toBeInTheDocument()
    })
  }

  it('renders null (no DOM node) for stat type — chart suppressed at AnswerCard level', () => {
    const { container } = render(<ChartWidget chart={makeSpec('stat')} />)
    expect(container.querySelector('[data-testid="chart-widget"]')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// emphasisFill — pure function tests for data-driven emphasis behavior
// These two fixtures prove the logic is NOT hardcoded to the first mark.
// ---------------------------------------------------------------------------

describe('emphasisFill — data-driven emphasis target', () => {
  const HIGHLIGHT = '#3b82f6'
  const MUTED = '#bfdbfe'

  it('highlights SP and mutes peers when emphasis_target is "SP"', () => {
    expect(emphasisFill('SP', 'SP', HIGHLIGHT, MUTED)).toBe(HIGHLIGHT)
    expect(emphasisFill('RJ', 'SP', HIGHLIGHT, MUTED)).toBe(MUTED)
    expect(emphasisFill('MG', 'SP', HIGHLIGHT, MUTED)).toBe(MUTED)
  })

  it('highlights RJ and mutes SP when emphasis_target is "RJ" — proves non-hardcoded', () => {
    expect(emphasisFill('RJ', 'RJ', HIGHLIGHT, MUTED)).toBe(HIGHLIGHT)
    expect(emphasisFill('SP', 'RJ', HIGHLIGHT, MUTED)).toBe(MUTED)
  })

  it('returns highlight for all marks when no emphasis_target is set', () => {
    expect(emphasisFill('SP', null, HIGHLIGHT, MUTED)).toBe(HIGHLIGHT)
    expect(emphasisFill('RJ', undefined, HIGHLIGHT, MUTED)).toBe(HIGHLIGHT)
  })
})
