/**
 * chartExport.ts — client-side export helpers for chart data.
 *
 * All functions are pure (no side-effects beyond triggering downloads)
 * so they can be unit-tested without a real browser environment, except
 * exportPNG which requires canvas rasterization (tested indirectly via helpers).
 */

export interface ProvenanceMeta {
  badge: string
  runDate: string
  rowCount: number
  product: string
}

/** Build provenance metadata from runtime context. */
export function buildProvenance(badge: string, rowCount: number): ProvenanceMeta {
  return {
    badge,
    runDate: new Date().toISOString().slice(0, 10),
    rowCount,
    product: 'Querio',
  }
}

/**
 * Serialize data rows to RFC 4180 CSV.
 * Keys are taken from the first row; order is stable across all rows.
 * Appends a provenance comment block if provenance is non-null.
 */
export function dataToCSV(
  data: Record<string, unknown>[],
  provenance: ProvenanceMeta | null,
): string {
  if (data.length === 0) return ''

  // data[0] is guaranteed non-undefined after the length guard above.
  // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
  const keys = Object.keys(data[0]!)

  function escapeCell(v: unknown): string {
    const s = v === null || v === undefined ? '' : String(v)
    // Quote cells that contain comma, double-quote, or line breaks
    return /[,"\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }

  const lines: string[] = [
    keys.join(','),
    ...data.map((row) => keys.map((k) => escapeCell(row[k])).join(',')),
  ]

  if (provenance) {
    lines.push('')
    lines.push(
      `# ${provenance.product} | badge: ${provenance.badge} | run_date: ${provenance.runDate} | row_count: ${provenance.rowCount}`,
    )
  }

  return lines.join('\n')
}

/**
 * Clone an SVG element and return its serialized string.
 * If provenance is provided, appends a visible text footer inside the SVG
 * by bumping the SVG height and appending a <text> element.
 * Does not mutate the live DOM.
 */
export function svgElementToString(
  svgEl: SVGSVGElement,
  provenance: ProvenanceMeta | null,
): string {
  const clone = svgEl.cloneNode(true) as SVGSVGElement

  // Force white background so theme colors never bleed into the export
  const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
  bgRect.setAttribute('x', '0')
  bgRect.setAttribute('y', '0')
  bgRect.setAttribute('width', '100%')
  bgRect.setAttribute('height', '100%')
  bgRect.setAttribute('fill', '#ffffff')
  clone.insertBefore(bgRect, clone.firstChild)

  if (provenance) {
    const label = `${provenance.product} | badge: ${provenance.badge} | ${provenance.runDate} | ${provenance.rowCount} rows`

    // Bump height to make room for footer text
    const rawH = parseFloat(clone.getAttribute('height') ?? '300')
    const currentH = Number.isFinite(rawH) && rawH > 0 ? rawH : 300
    const newH = currentH + 28
    clone.setAttribute('height', String(newH))

    const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    textEl.setAttribute('x', '8')
    textEl.setAttribute('y', String(currentH + 18))
    textEl.setAttribute('font-size', '11')
    textEl.setAttribute('fill', '#888888')
    textEl.setAttribute('font-family', 'sans-serif')
    textEl.setAttribute('data-provenance', 'true')
    textEl.textContent = label
    clone.appendChild(textEl)
  }

  return new XMLSerializer().serializeToString(clone)
}

// ---------------------------------------------------------------------------
// Download triggers
// ---------------------------------------------------------------------------

function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function downloadString(filename: string, content: string, mimeType: string): void {
  downloadBlob(filename, new Blob([content], { type: mimeType }))
}

// ---------------------------------------------------------------------------
// Public export actions
// ---------------------------------------------------------------------------

/** Export chart data rows as a CSV file. */
export function exportCSV(
  data: Record<string, unknown>[],
  provenance: ProvenanceMeta | null,
  filename = 'querio-export.csv',
): void {
  const csv = dataToCSV(data, provenance)
  downloadString(filename, csv, 'text/csv;charset=utf-8')
}

/** Export the rendered chart's SVG DOM node as a .svg file. */
export function exportSVG(
  svgEl: SVGSVGElement,
  provenance: ProvenanceMeta | null,
  filename = 'querio-chart.svg',
): void {
  const svgString = svgElementToString(svgEl, provenance)
  downloadString(filename, svgString, 'image/svg+xml;charset=utf-8')
}

/**
 * Rasterize the rendered chart SVG to a 2x PNG on a white background.
 * Canvas-based — cannot be unit-tested in jsdom; test pure helpers (dataToCSV,
 * svgElementToString) instead and rely on browser integration for canvas path.
 */
export async function exportPNG(
  svgEl: SVGSVGElement,
  provenance: ProvenanceMeta | null,
  filename = 'querio-chart.png',
): Promise<void> {
  // Serialize with provenance already embedded so the PNG includes the footer
  const svgString = svgElementToString(svgEl, provenance)

  const rawW = parseFloat(svgEl.getAttribute('width') ?? '0')
  const rawH = parseFloat(svgEl.getAttribute('height') ?? '0')
  const rect = svgEl.getBoundingClientRect()
  const w = rawW > 0 ? rawW : rect.width || 600
  const h = rawH > 0 ? rawH : rect.height || 300

  // Extra height for provenance footer already included in svgString via svgElementToString
  const exportH = provenance ? h + 28 : h
  const scale = 2

  const canvas = document.createElement('canvas')
  canvas.width = Math.round(w * scale)
  canvas.height = Math.round(exportH * scale)

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // White background — required regardless of current UI theme
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.scale(scale, scale)

  const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)

  await new Promise<void>((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      ctx.drawImage(img, 0, 0)
      URL.revokeObjectURL(url)
      resolve()
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('SVG rasterization failed'))
    }
    img.src = url
  })

  canvas.toBlob((blob) => {
    if (blob) downloadBlob(filename, blob)
  }, 'image/png')
}
