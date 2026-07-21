import type { ChartSpecResponse } from '../types/api'

/**
 * Verify that every column key referenced by a chart spec exists in the
 * actual query-result column set.
 *
 * If resultColumns is empty we cannot prove a mismatch, so we treat the
 * spec as valid rather than emitting a false-positive fallback (e.g. when
 * resultRows is null/undefined because the backend omitted it).
 */
export function validateChartColumns(
  chart: ChartSpecResponse,
  resultColumns: string[],
): boolean {
  if (resultColumns.length === 0) return true

  const colSet = new Set(resultColumns)

  if (!colSet.has(chart.x_key)) return false
  if (!colSet.has(chart.y_key)) return false

  if (chart.y_keys) {
    for (const key of chart.y_keys) {
      if (!colSet.has(key)) return false
    }
  }

  return true
}
