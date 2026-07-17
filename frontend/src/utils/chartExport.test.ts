import { describe, it, expect } from 'vitest'
import { dataToCSV, buildProvenance } from './chartExport'

const FIXTURE_DATA: Record<string, unknown>[] = [
  { month: 'Jan', revenue: 2100000 },
  { month: 'Feb', revenue: 1950000 },
  { month: 'Mar', revenue: 2340000 },
]

describe('dataToCSV', () => {
  it('round-trips result set exactly — header + values, no reformatting', () => {
    const csv = dataToCSV(FIXTURE_DATA, null)
    const lines = csv.split('\n')
    expect(lines[0]).toBe('month,revenue')
    expect(lines[1]).toBe('Jan,2100000')
    expect(lines[2]).toBe('Feb,1950000')
    expect(lines[3]).toBe('Mar,2340000')
    // No extra lines beyond data rows
    expect(lines).toHaveLength(4)
  })

  it('appends provenance footer when provenance is provided', () => {
    const provenance = buildProvenance('verified', FIXTURE_DATA.length)
    const csv = dataToCSV(FIXTURE_DATA, provenance)
    const lines = csv.split('\n')
    // Last line is the provenance comment
    const footer = lines[lines.length - 1]
    expect(footer).toContain('Querio')
    expect(footer).toContain('badge: verified')
    expect(footer).toContain('row_count: 3')
    expect(footer).toMatch(/run_date: \d{4}-\d{2}-\d{2}/)
  })

  it('omits provenance footer when provenance is null', () => {
    const csv = dataToCSV(FIXTURE_DATA, null)
    expect(csv).not.toContain('Querio')
    expect(csv).not.toContain('badge:')
  })
})
