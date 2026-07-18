import { describe, it, expect } from 'vitest'
import { dataToCSV, buildProvenance, svgElementToString } from './chartExport'

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

// ---------------------------------------------------------------------------
// svgElementToString — white background + provenance footer (SRS VIZ-6, PRIN-4)
// ---------------------------------------------------------------------------

describe('svgElementToString', () => {
  function makeSvg(width = '600', height = '300'): SVGSVGElement {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg') as SVGSVGElement
    svg.setAttribute('width', width)
    svg.setAttribute('height', height)
    return svg
  }

  it('inserts white background rect when provenance is provided', () => {
    const provenance = buildProvenance('verified', 3)
    const result = svgElementToString(makeSvg(), provenance)
    expect(result).toMatch(/<rect[^>]+fill="#ffffff"/)
  })

  it('includes data-provenance text footer with badge and product when provenance is provided', () => {
    const provenance = buildProvenance('verified', 3)
    const result = svgElementToString(makeSvg(), provenance)
    expect(result).toContain('data-provenance="true"')
    expect(result).toContain('Querio')
    expect(result).toContain('badge: verified')
  })

  it('omits data-provenance element and preserves original height when provenance is null', () => {
    const result = svgElementToString(makeSvg('600', '300'), null)
    expect(result).not.toContain('data-provenance')
    // height attribute must remain at original value — no footer bump
    expect(result).toContain('height="300"')
  })
})
