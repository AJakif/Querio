import type { ChartSpecResponse } from '../../types/api'
import {
  BarChart,
  LineChart,
  Bar,
  Line,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

// ---------------------------------------------------------------------------
// Palette — full saturation vs muted for emphasis logic
// ---------------------------------------------------------------------------

const HIGHLIGHT = '#3b82f6'
const MUTED = '#bfdbfe'
const NEG_HIGHLIGHT = '#ef4444'
const NEG_MUTED = '#fecaca'

/** Ordered palette for stacked-bar series; index wraps */
const STACK_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#f97316']
const STACK_MUTED = ['#bfdbfe', '#d1fae5', '#fde68a', '#ede9fe', '#fed7aa']

// ---------------------------------------------------------------------------
// Pure helper — exported so tests can verify data-driven emphasis without
// depending on SVG render output from Recharts in jsdom.
// ---------------------------------------------------------------------------

/**
 * Returns `highlight` when `xVal` matches `emphasisTarget` (or when no target
 * is set — all marks are equally prominent). Returns `muted` otherwise.
 */
export function emphasisFill(
  xVal: unknown,
  emphasisTarget: string | null | undefined,
  highlight: string,
  muted: string,
): string {
  if (!emphasisTarget) return highlight
  return String(xVal) === emphasisTarget ? highlight : muted
}

// ---------------------------------------------------------------------------
// Per-form renderers
// ---------------------------------------------------------------------------

function BarForm({ chart }: { chart: ChartSpecResponse }) {
  const { data, x_key, y_key, emphasis_target } = chart
  return (
    <BarChart data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey={x_key} />
      <YAxis />
      <Tooltip />
      <Bar dataKey={y_key} isAnimationActive={false}>
        {data.map((entry, idx) => (
          <Cell
            key={idx}
            fill={emphasisFill(entry[x_key], emphasis_target, HIGHLIGHT, MUTED)}
          />
        ))}
      </Bar>
    </BarChart>
  )
}

function HistogramForm({ chart }: { chart: ChartSpecResponse }) {
  const { data, x_key, y_key, emphasis_target } = chart
  return (
    // barCategoryGap=0 removes inter-bar gap — canonical histogram look
    <BarChart data={data} barCategoryGap={0}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey={x_key} />
      <YAxis />
      <Tooltip />
      <Bar dataKey={y_key} isAnimationActive={false}>
        {data.map((entry, idx) => (
          <Cell
            key={idx}
            fill={emphasisFill(entry[x_key], emphasis_target, HIGHLIGHT, MUTED)}
          />
        ))}
      </Bar>
    </BarChart>
  )
}

function LineForm({ chart }: { chart: ChartSpecResponse }) {
  const { data, x_key, y_key } = chart
  return (
    <LineChart data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey={x_key} />
      <YAxis />
      <Tooltip />
      <Line
        type="monotone"
        dataKey={y_key}
        stroke={HIGHLIGHT}
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  )
}

function DivergingBarForm({ chart }: { chart: ChartSpecResponse }) {
  const { data, x_key, y_key, emphasis_target } = chart
  return (
    <BarChart data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey={x_key} />
      <YAxis />
      <Tooltip />
      <Bar dataKey={y_key} isAnimationActive={false}>
        {data.map((entry, idx) => {
          const val = entry[y_key] as number
          const isEmphasis =
            !emphasis_target || String(entry[x_key]) === emphasis_target
          const fill =
            val >= 0
              ? isEmphasis
                ? HIGHLIGHT
                : MUTED
              : isEmphasis
                ? NEG_HIGHLIGHT
                : NEG_MUTED
          return <Cell key={idx} fill={fill} />
        })}
      </Bar>
    </BarChart>
  )
}

function StackedBarForm({ chart }: { chart: ChartSpecResponse }) {
  const { data, x_key, y_keys, y_key, emphasis_target } = chart
  const keys = y_keys && y_keys.length > 0 ? y_keys : [y_key]

  return (
    <BarChart data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey={x_key} />
      <YAxis />
      <Tooltip />
      <Legend />
      {keys.map((key, seriesIdx) => (
        <Bar key={key} dataKey={key} stackId="a" isAnimationActive={false}>
          {data.map((entry, idx) => {
            const isEmphasis =
              !emphasis_target || String(entry[x_key]) === emphasis_target
            const fill = isEmphasis
              ? STACK_COLORS[seriesIdx % STACK_COLORS.length]
              : STACK_MUTED[seriesIdx % STACK_MUTED.length]
            return <Cell key={idx} fill={fill} />
          })}
        </Bar>
      ))}
    </BarChart>
  )
}

// ---------------------------------------------------------------------------
// Dispatch — maps chart_type to its form renderer
// ---------------------------------------------------------------------------

function renderChart(chart: ChartSpecResponse) {
  switch (chart.chart_type) {
    case 'bar':
    case 'emphasis':
      // 'emphasis' is a bar form where emphasis_target is analytically required
      return <BarForm chart={chart} />
    case 'histogram':
      return <HistogramForm chart={chart} />
    case 'line':
      return <LineForm chart={chart} />
    case 'diverging_bar':
      return <DivergingBarForm chart={chart} />
    case 'stacked_bar':
      return <StackedBarForm chart={chart} />
    case 'stat':
      // stat is handled at AnswerCard level; ChartWidget should not be called for stat
      return null
    default: {
      // exhaustiveness guard — unknown types fall back to bar
      const _exhaustive: never = chart.chart_type
      void _exhaustive
      return <BarForm chart={chart} />
    }
  }
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

interface ChartWidgetProps {
  chart: ChartSpecResponse
  /**
   * Citation-selection dimming target — x_key value of the cited row.
   * When set, overrides the analytical emphasis_target so all marks except
   * the cited one dim. Cleared when the user taps the same cite again.
   * This is SEPARATE state from chart_spec.emphasis_target (TRUST-9 selection
   * vs. analytical emphasis from slice 8 — do not conflate them).
   */
  citationTarget?: string | null
}

export function ChartWidget({ chart, citationTarget }: ChartWidgetProps) {
  if (chart.chart_type === 'stat') return null

  // When a citation is active, override emphasis_target with the cited x_key value.
  // When cleared (null/undefined), fall back to the analytical emphasis_target.
  const effectiveChart =
    citationTarget != null ? { ...chart, emphasis_target: citationTarget } : chart

  const inner = renderChart(effectiveChart)
  if (!inner) return null

  return (
    <div data-testid="chart-widget" className="chart-widget">
      {chart.title && <h4 className="chart-widget__title">{chart.title}</h4>}
      <ResponsiveContainer width="100%" height={300}>
        {inner}
      </ResponsiveContainer>
    </div>
  )
}
