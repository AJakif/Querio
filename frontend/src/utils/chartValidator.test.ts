import { describe, it, expect } from 'vitest'
import { validateChartColumns } from './chartValidator'
import type { ChartSpecResponse } from '../types/api'

const base: ChartSpecResponse = {
  chart_type: 'bar',
  title: 'Test',
  data: [],
  x_key: 'region',
  y_key: 'revenue',
}

describe('validateChartColumns', () => {
  it('returns true when all referenced columns exist', () => {
    expect(validateChartColumns(base, ['region', 'revenue'])).toBe(true)
  })

  it('returns false when x_key is missing from result columns', () => {
    expect(validateChartColumns(base, ['revenue'])).toBe(false)
  })

  it('returns false when y_key is missing from result columns', () => {
    expect(validateChartColumns(base, ['region'])).toBe(false)
  })

  it('returns false when one of y_keys is missing', () => {
    const spec: ChartSpecResponse = { ...base, y_keys: ['q1', 'q2'] }
    expect(validateChartColumns(spec, ['region', 'revenue', 'q1'])).toBe(false)
  })

  it('skips validation and returns true when resultColumns is empty (no result set available)', () => {
    expect(validateChartColumns(base, [])).toBe(true)
  })
})
