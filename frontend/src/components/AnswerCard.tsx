import { useRef, useState } from 'react'
import type { AnswerSpec, BadgeState, Assumption, Headline, ValidationResultResponse, TraceStep } from '../types/api'
import { ChartWidget } from './charts/ChartWidget'
import { useProvenanceSetting } from '../hooks/useProvenanceSetting'
import { buildProvenance, exportCSV, exportSVG, exportPNG } from '../utils/chartExport'
import { CitedSummary } from './CitedSummary'

interface AnswerCardProps {
  spec: AnswerSpec
  badge: BadgeState
  verifierName?: string | null
  onSend?: (question: string) => void
  sql?: { sql: string; explanation: string } | null
  validation?: ValidationResultResponse | null
  traceSteps?: TraceStep[]
  resultRows?: Record<string, unknown>[] | null
}

// ---------------------------------------------------------------------------
// Badge row
// ---------------------------------------------------------------------------

interface BadgeConfig {
  icon: string
  label: string
  className: string
}

const BADGE_CONFIG: Record<BadgeState, BadgeConfig> = {
  unverified: { icon: '🕐', label: 'Unverified', className: 'badge--unverified' },
  verified: { icon: '✓', label: 'Verified', className: 'badge--verified' },
  needs_recheck: { icon: '⚠', label: 'Needs recheck', className: 'badge--recheck' },
  disputed: { icon: '✗', label: 'Disputed', className: 'badge--disputed' },
}

function BadgeRow({ badge, verifierName }: { badge: BadgeState; verifierName?: string | null }) {
  const { icon, label, className } = BADGE_CONFIG[badge]
  const displayLabel = badge === 'verified' && verifierName ? `Verified by ${verifierName}` : label
  return (
    <div data-testid="badge-row" className={`answer-card__badge ${className}`}>
      <span className="badge__icon" aria-hidden="true">{icon}</span>
      <span className="badge__label">{displayLabel}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Assumption line
// ---------------------------------------------------------------------------

function CloseCallChip({ assumption }: { assumption: Assumption }) {
  return (
    <div data-testid="close-call-chip" className="assumption-chip assumption-chip--close-call">
      <span className="chip__term">{assumption.term}</span>
      <span className="chip__reason">{assumption.resolution}</span>
    </div>
  )
}

function AssumptionLine({ assumptions }: { assumptions: Assumption[] }) {
  const closeCall = assumptions.filter((a) => a.close_call)
  const routine = assumptions.filter((a) => !a.close_call)

  return (
    <div data-testid="assumption-line" className="answer-card__assumptions">
      {closeCall.map((a) => (
        <CloseCallChip key={a.term} assumption={a} />
      ))}
      {routine.length > 0 && (
        <div className="assumption-compressed">
          {routine.map((a) => a.term).join(' · ')}
          {' ▾'}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Headline stat
// ---------------------------------------------------------------------------

function HeadlineStat({ headline }: { headline: Headline }) {
  const signClass =
    headline.sign === 'positive'
      ? 'headline--positive'
      : headline.sign === 'negative'
        ? 'headline--negative'
        : ''

  return (
    <div data-testid="headline-stat" className="answer-card__headline">
      <div className={`headline__value ${signClass}`}>{headline.value}</div>
      <div className="headline__label">{headline.label}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Follow-ups strip
// ---------------------------------------------------------------------------

function FollowUpsStrip({
  followups,
  onSend,
}: {
  followups: string[]
  onSend?: (q: string) => void
}) {
  const chips = followups.slice(0, 3)
  if (!chips.length) return null
  return (
    <div data-testid="followups-strip" className="answer-card__followups">
      {chips.map((q) => (
        <button
          key={q}
          type="button"
          className="followup-chip"
          onClick={() => onSend?.(q)}
          title={q}
        >
          {q}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Export buttons — PNG / SVG / CSV with provenance footer toggle
// ---------------------------------------------------------------------------

interface ExportButtonsProps {
  badge: BadgeState
  data: Record<string, unknown>[]
  chartContainerRef: React.RefObject<HTMLDivElement | null>
  hasChart: boolean
}

function ExportButtons({ badge, data, chartContainerRef, hasChart }: ExportButtonsProps) {
  const [provenanceEnabled, setProvenanceEnabled] = useProvenanceSetting()

  function getSvgEl(): SVGSVGElement | null {
    return chartContainerRef.current?.querySelector<SVGSVGElement>('svg') ?? null
  }

  function getProvenance() {
    return provenanceEnabled ? buildProvenance(badge, data.length) : null
  }

  function handlePNG(): void {
    const svgEl = getSvgEl()
    if (!svgEl) return
    void exportPNG(svgEl, getProvenance())
  }

  function handleSVG(): void {
    const svgEl = getSvgEl()
    if (!svgEl) return
    exportSVG(svgEl, getProvenance())
  }

  function handleCSV(): void {
    exportCSV(data, getProvenance())
  }

  return (
    <div data-testid="export-buttons" className="answer-card__export">
      {hasChart && (
        <>
          <button
            type="button"
            className="export-btn"
            onClick={handlePNG}
            aria-label="Export as PNG"
          >
            PNG
          </button>
          <button
            type="button"
            className="export-btn"
            onClick={handleSVG}
            aria-label="Export as SVG"
          >
            SVG
          </button>
        </>
      )}
      <button
        type="button"
        className="export-btn"
        onClick={handleCSV}
        aria-label="Export as CSV"
      >
        CSV
      </button>
      <label className="export-provenance-toggle">
        <input
          type="checkbox"
          checked={provenanceEnabled}
          onChange={(e) => setProvenanceEnabled(e.target.checked)}
          aria-label="Include provenance footer in exports"
        />
        <span className="export-provenance-label">Provenance</span>
      </label>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Workbench drawer — navy/cyan/amber palette, JetBrains Mono, hard seam
// ---------------------------------------------------------------------------

function WorkbenchDrawer({
  traceSteps,
  sql,
  validation,
  suppressionReason,
}: {
  traceSteps?: TraceStep[]
  sql?: { sql: string; explanation: string } | null
  validation?: ValidationResultResponse | null
  suppressionReason?: string | null
}) {
  return (
    <div data-testid="workbench-drawer" className="workbench-drawer">
      {/* Trace */}
      <section className="wb-section">
        <h4 className="wb-section__title">Trace</h4>
        {traceSteps && traceSteps.length > 0 ? (
          <ol className="wb-trace" data-testid="workbench-trace">
            {traceSteps.map((step, i) => (
              <li key={i} className="wb-trace__step">
                <span className="wb-trace__stage">{step.stage}</span>
                {Object.entries(step.detail).map(([k, v]) => (
                  <span key={k} className="wb-trace__detail">{k}: {String(v)}</span>
                ))}
              </li>
            ))}
          </ol>
        ) : (
          <p className="wb-empty" data-testid="workbench-trace">No trace captured.</p>
        )}
        {suppressionReason && (
          <p className="wb-suppression" data-testid="workbench-suppression">
            Chart suppressed: {suppressionReason}
          </p>
        )}
      </section>

      {/* SQL */}
      {sql && (
        <section className="wb-section">
          <h4 className="wb-section__title">Generated SQL</h4>
          <pre className="wb-code" data-testid="workbench-sql"><code>{sql.sql}</code></pre>
        </section>
      )}

      {/* Dependency fingerprints */}
      {validation && validation.fingerprints.length > 0 && (
        <section className="wb-section">
          <h4 className="wb-section__title">Dependency Fingerprints</h4>
          <table className="wb-fingerprints" data-testid="workbench-fingerprints">
            <thead>
              <tr>
                <th>Table</th>
                <th>Column</th>
                <th>Schema hash</th>
              </tr>
            </thead>
            <tbody>
              {validation.fingerprints.map((fp, i) => (
                <tr key={i}>
                  <td>{fp.table}</td>
                  <td>{fp.column}</td>
                  <td className="wb-hash">{fp.schema_hash.slice(0, 8)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Cost estimate */}
      {validation != null && (
        <section className="wb-section">
          <h4 className="wb-section__title">Cost estimate</h4>
          <span className="wb-cost" data-testid="workbench-cost">
            {validation.scan_cost.toLocaleString()} rows scanned
          </span>
        </section>
      )}
    </div>
  )
}

function WorkbenchToggle({
  traceSteps,
  sql,
  validation,
  suppressionReason,
}: {
  traceSteps?: TraceStep[]
  sql?: { sql: string; explanation: string } | null
  validation?: ValidationResultResponse | null
  suppressionReason?: string | null
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className="answer-card__workbench">
      <button
        type="button"
        data-testid="workbench-toggle"
        className="workbench-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="workbench-toggle__label">show the work</span>
        <span className="workbench-toggle__caret" aria-hidden="true">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <WorkbenchDrawer
          traceSteps={traceSteps}
          sql={sql}
          validation={validation}
          suppressionReason={suppressionReason}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// AnswerCard — routes on response_type
//   ROUTE-1 'stat'  → badge → assumption → headline (no chart)
//   ROUTE-2 'chart' → badge → assumption → headline → chart → restatement
//
// response_type defaults to 'chart' when chart_spec is present, 'stat' otherwise,
// so specs that omit the field (e.g. slice-7 test fixtures) stay on ROUTE-1.
// ---------------------------------------------------------------------------

export function AnswerCard({ spec, badge, verifierName, onSend, sql, validation, traceSteps, resultRows }: AnswerCardProps) {
  const responseType =
    spec.response_type ?? (spec.chart_spec ? 'chart' : 'stat')

  // Citation selection state — separate from chart_spec.emphasis_target (analytical emphasis).
  // Set when user taps a chart-addressable row-cite; cleared on tap-again or computation-cite.
  const [citationTarget, setCitationTarget] = useState<string | null>(null)

  // Ref on the chart wrapper div — used by ExportButtons to locate the SVG for PNG/SVG export.
  const chartContainerRef = useRef<HTMLDivElement | null>(null)

  return (
    <div data-testid="answer-card" className="answer-card">
      {/* Fixed order: badge → assumption → headline (normative per Blueprint) */}
      <BadgeRow badge={badge} verifierName={verifierName} />
      <AssumptionLine assumptions={spec.assumptions_ref} />
      <HeadlineStat headline={spec.headline} />
      {responseType === 'chart' && spec.chart_spec && (
        <div ref={chartContainerRef}>
          <ChartWidget chart={spec.chart_spec} citationTarget={citationTarget} />
        </div>
      )}
      {/* Cited summary (slice 9): claims with tappable markers + source panel.
          Rendered for both chart and stat routes whenever claims exist. */}
      {(spec.claims.length > 0 || spec.dropped_claim_count > 0) && (
        <CitedSummary
          claims={spec.claims}
          droppedClaimCount={spec.dropped_claim_count}
          chartSpec={spec.chart_spec}
          onCitationTargetChange={setCitationTarget}
        />
      )}
      <p data-testid="answer-restatement" className="answer-card__restatement">
        {spec.restatement}
      </p>

      {/* Follow-ups + export actions row */}
      <div className="answer-card__actions">
        <FollowUpsStrip followups={spec.followups} onSend={onSend} />
        <ExportButtons
          badge={badge}
          data={resultRows ?? spec.chart_spec?.data ?? []}
          chartContainerRef={chartContainerRef}
          hasChart={responseType === 'chart' && !!spec.chart_spec}
        />
      </div>

      {/* Workbench toggle + drawer — full-width navy strip at card bottom */}
      <WorkbenchToggle
        traceSteps={traceSteps}
        sql={sql}
        validation={validation}
        suppressionReason={spec.suppression_reason}
      />
    </div>
  )
}
