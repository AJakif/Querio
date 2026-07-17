import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CitedSummary, isChartAddressable, getChartTarget } from './CitedSummary'
import type { Claim, ChartSpecResponse } from '../types/api'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const chartSpec: ChartSpecResponse = {
  chart_type: 'bar',
  title: 'Revenue by Region',
  data: [
    { region: 'SP', revenue: 4200000 },
    { region: 'RJ', revenue: 1350000 },
  ],
  x_key: 'region',
  y_key: 'revenue',
  emphasis_target: 'SP',
}

const rowClaim: Claim = {
  sentence: 'SP generated 4.2M in revenue.',
  type: 'row',
  cells: [{ region: 'SP', revenue: 4200000 }],
}

const computationClaim: Claim = {
  sentence: 'SP revenue is 3.1× the RJ figure.',
  type: 'computation',
  cells: [],
  operation: 'division',
  operands: [4200000, 1350000],
  value: 3.11,
}

const notAddressableClaim: Claim = {
  // data folded into "other" — not in chart
  sentence: 'Other regions contributed 2.1M.',
  type: 'row',
  cells: [{ region: 'other', revenue: 2100000 }],
}

// ---------------------------------------------------------------------------
// Unit helpers
// ---------------------------------------------------------------------------

describe('isChartAddressable', () => {
  it('returns true when claim cells match a chart x_key value', () => {
    expect(isChartAddressable(rowClaim, chartSpec)).toBe(true)
  })

  it('returns false for computation type regardless of chart', () => {
    expect(isChartAddressable(computationClaim, chartSpec)).toBe(false)
  })

  it('returns false when no cell matches chart data (folded into other)', () => {
    expect(isChartAddressable(notAddressableClaim, chartSpec)).toBe(false)
  })
})

describe('getChartTarget', () => {
  it('returns the x_key value of the first matching cell', () => {
    expect(getChartTarget(rowClaim, chartSpec)).toBe('SP')
  })
})

// ---------------------------------------------------------------------------
// Load-bearing component tests (3)
// ---------------------------------------------------------------------------

describe('CitedSummary — linked selection', () => {
  it('tapping a row-cite dims chart (calls onCitationTargetChange with x_key) and opens source panel', async () => {
    const onCitationTargetChange = vi.fn()
    render(
      <CitedSummary
        claims={[rowClaim]}
        droppedClaimCount={0}
        chartSpec={chartSpec}
        onCitationTargetChange={onCitationTargetChange}
      />,
    )

    expect(screen.queryByTestId('source-panel')).toBeNull()

    await userEvent.click(screen.getByTestId('cite-marker-0'))

    // Chart dim callback with the citation's x_key value
    expect(onCitationTargetChange).toHaveBeenCalledWith('SP')
    // Source panel opens with row data
    const panel = screen.getByTestId('source-panel')
    expect(panel).toBeInTheDocument()
    expect(panel).toHaveTextContent('SP')
    expect(panel).toHaveTextContent('4200000')
  })

  it('tapping the same row-cite again clears dimming and closes source panel', async () => {
    const onCitationTargetChange = vi.fn()
    render(
      <CitedSummary
        claims={[rowClaim]}
        droppedClaimCount={0}
        chartSpec={chartSpec}
        onCitationTargetChange={onCitationTargetChange}
      />,
    )

    const marker = screen.getByTestId('cite-marker-0')
    await userEvent.click(marker)   // open
    await userEvent.click(marker)   // close

    // Second call must be null — clears dim
    expect(onCitationTargetChange).toHaveBeenLastCalledWith(null)
    expect(screen.queryByTestId('source-panel')).toBeNull()
  })

  it('tapping a computation-cite opens source panel with operation but does NOT dim the chart', async () => {
    const onCitationTargetChange = vi.fn()
    render(
      <CitedSummary
        claims={[computationClaim]}
        droppedClaimCount={0}
        chartSpec={chartSpec}
        onCitationTargetChange={onCitationTargetChange}
      />,
    )

    await userEvent.click(screen.getByTestId('cite-marker-0'))

    // Dim callback called with null — computation is not chart-addressable
    expect(onCitationTargetChange).toHaveBeenCalledWith(null)
    // Source panel opens and shows operation
    const panel = screen.getByTestId('source-panel')
    expect(panel).toBeInTheDocument()
    expect(panel).toHaveTextContent('division')
  })
})

// ---------------------------------------------------------------------------
// Additional load-bearing: TRUST-9 note + restatement exemption
// ---------------------------------------------------------------------------

describe('CitedSummary — TRUST-9 and edge cases', () => {
  it('shows TRUST-9 note when dropped_claim_count > 0', () => {
    render(
      <CitedSummary
        claims={[]}
        droppedClaimCount={2}
        onCitationTargetChange={vi.fn()}
      />,
    )
    const note = screen.getByTestId('trust9-note')
    expect(note).toHaveTextContent("2 insights couldn't be verified against the data")
  })

  it('opens source panel only (no dim) for a row-cite not in chart data', async () => {
    const onCitationTargetChange = vi.fn()
    render(
      <CitedSummary
        claims={[notAddressableClaim]}
        droppedClaimCount={0}
        chartSpec={chartSpec}
        onCitationTargetChange={onCitationTargetChange}
      />,
    )

    await userEvent.click(screen.getByTestId('cite-marker-0'))

    expect(onCitationTargetChange).toHaveBeenCalledWith(null)
    expect(screen.getByTestId('source-panel')).toBeInTheDocument()
  })
})
