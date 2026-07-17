import { useState } from 'react'
import type { Claim, ChartSpecResponse } from '../types/api'

// ---------------------------------------------------------------------------
// Helpers — chart-addressability
// ---------------------------------------------------------------------------

/**
 * A row-claim is chart-addressable when the chart exists AND at least one of
 * the claim's cells has an x_key value that appears in chart.data.
 * Computation-claims and row-claims whose data folded into "other" are NOT.
 */
export function isChartAddressable(
  claim: Claim,
  chartSpec: ChartSpecResponse | null | undefined,
): boolean {
  if (claim.type !== 'row' || !chartSpec) return false
  const xVals = new Set(chartSpec.data.map((d) => String(d[chartSpec.x_key])))
  return claim.cells.some((cell) => xVals.has(String(cell[chartSpec.x_key])))
}

/**
 * Returns the x_key value from the claim's first matching cell, or null when
 * no cell is chart-addressable.
 */
export function getChartTarget(
  claim: Claim,
  chartSpec: ChartSpecResponse,
): string | null {
  const xVals = new Set(chartSpec.data.map((d) => String(d[chartSpec.x_key])))
  const match = claim.cells.find((cell) => xVals.has(String(cell[chartSpec.x_key])))
  return match ? String(match[chartSpec.x_key]) : null
}

// ---------------------------------------------------------------------------
// Source panel
// ---------------------------------------------------------------------------

function SourcePanel({ claim }: { claim: Claim }) {
  if (claim.type === 'computation') {
    return (
      <div data-testid="source-panel" className="source-panel source-panel--computation">
        <h5 className="source-panel__title">Computation</h5>
        {claim.operation && (
          <p className="source-panel__operation">{claim.operation}</p>
        )}
        {claim.operands && claim.operands.length > 0 && (
          <p className="source-panel__operands">
            Operands: {claim.operands.join(', ')}
          </p>
        )}
        {claim.value != null && (
          <p className="source-panel__result">Result: {claim.value}</p>
        )}
      </div>
    )
  }

  // row type
  const firstCell = claim.cells[0]
  if (!firstCell) return null
  const cols = Object.keys(firstCell)

  return (
    <div data-testid="source-panel" className="source-panel source-panel--rows">
      <h5 className="source-panel__title">Source rows</h5>
      <div className="source-panel__scroll">
        <table className="source-panel__table">
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {claim.cells.map((row, i) => (
              <tr key={i}>
                {cols.map((c) => (
                  <td key={c}>{String(row[c] ?? '')}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Citation marker + single claim sentence
// ---------------------------------------------------------------------------

interface CitedClaimProps {
  claim: Claim
  index: number
  selected: boolean
  onTap: (index: number) => void
}

function CitedClaim({ claim, index, selected, onTap }: CitedClaimProps) {
  const markerLabel = String(index + 1)
  return (
    <span className={`cited-claim${selected ? ' cited-claim--active' : ''}`}>
      {claim.sentence}
      <button
        type="button"
        data-testid={`cite-marker-${index}`}
        className="cite-marker"
        aria-label={`Citation ${markerLabel}${selected ? ' — tap to close' : ''}`}
        aria-pressed={selected}
        onClick={() => onTap(index)}
      >
        [{markerLabel}]
      </button>
    </span>
  )
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

interface CitedSummaryProps {
  claims: Claim[]
  droppedClaimCount: number
  chartSpec?: ChartSpecResponse | null
  /** Called when the citation selection changes. Pass null to clear dimming. */
  onCitationTargetChange: (target: string | null) => void
}

export function CitedSummary({
  claims,
  droppedClaimCount,
  chartSpec,
  onCitationTargetChange,
}: CitedSummaryProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  if (!claims.length && droppedClaimCount === 0) return null

  function handleCiteTap(index: number) {
    if (selectedIndex === index) {
      // Toggle off
      setSelectedIndex(null)
      onCitationTargetChange(null)
    } else {
      setSelectedIndex(index)
      const claim = claims[index]
      if (!claim) return
      if (chartSpec && isChartAddressable(claim, chartSpec)) {
        onCitationTargetChange(getChartTarget(claim, chartSpec))
      } else {
        // computation-cite or data not in chart: open panel only, no dim
        onCitationTargetChange(null)
      }
    }
  }

  const selectedClaim = selectedIndex != null ? (claims[selectedIndex] ?? null) : null

  return (
    <div data-testid="cited-summary" className="cited-summary">
      {/* TRUST-9 — dropped claims note */}
      {droppedClaimCount > 0 && (
        <p data-testid="trust9-note" className="cited-summary__trust9">
          {droppedClaimCount} insight{droppedClaimCount !== 1 ? 's' : ''} couldn&apos;t be verified
          against the data.
        </p>
      )}

      {/* Claim sentences with tappable citation markers */}
      {claims.length > 0 && (
        <p className="cited-summary__body">
          {claims.map((claim, i) => (
            <CitedClaim
              key={i}
              claim={claim}
              index={i}
              selected={selectedIndex === i}
              onTap={handleCiteTap}
            />
          ))}
        </p>
      )}

      {/* Source panel — shown below the summary when a cite is selected */}
      {selectedClaim && <SourcePanel claim={selectedClaim} />}
    </div>
  )
}
