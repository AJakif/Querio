import { useState } from 'react'
import type { UploadPreviewResponse } from '../api/uploadApi'

interface SchemaPreviewProps {
  preview: UploadPreviewResponse
  onConfirm: (previewToken: string, contextNote: string) => void
  onCancel: () => void
}

function StatsCell({ col }: { col: UploadPreviewResponse['columns'][number] }) {
  const s = col.stats
  if (col.inferred_type === 'integer' || col.inferred_type === 'numeric') {
    const parts: string[] = []
    if (s.min_value !== null) parts.push(`Min: ${s.min_value}`)
    if (s.max_value !== null) parts.push(`Max: ${s.max_value}`)
    if (s.mean_value !== null) parts.push(`Mean: ${s.mean_value}`)
    return <span className="stats-numeric">{parts.join(' · ')}</span>
  }

  if (s.top_values && s.top_values.length > 0) {
    return (
      <span className="stats-top">
        {s.top_values.map((t, i) => (
          <span key={i} className="stats-top-item">
            {t.value}
            <span className="stats-top-count">{t.count}</span>
            {i < s.top_values!.length - 1 && ', '}
          </span>
        ))}
      </span>
    )
  }

  return <span className="stats-empty">—</span>
}

export function SchemaPreview({ preview, onConfirm, onCancel }: SchemaPreviewProps) {
  const [contextNote, setContextNote] = useState('')

  return (
    <div className="schema-preview">
      <h3 className="schema-preview-title">Schema Preview</h3>
      <p className="schema-preview-meta">
        {preview.total_rows.toLocaleString()} rows &middot; {preview.columns.length} columns
      </p>

      <div className="schema-table-wrapper">
        <table className="schema-table">
          <thead>
            <tr>
              <th>Column</th>
              <th>Type</th>
              <th>Null %</th>
              <th>Distribution</th>
            </tr>
          </thead>
          <tbody>
            {preview.columns.map((col) => (
              <tr key={col.name}>
                <td className="schema-col-name">{col.name}</td>
                <td>
                  <span className={`schema-type-badge schema-type-${col.inferred_type}`}>
                    {col.inferred_type}
                  </span>
                </td>
                <td className="stats-null-pct">{col.stats.null_percentage}%</td>
                <td className="stats-dist"><StatsCell col={col} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="schema-sample-details">
        <summary>Sample rows ({preview.sample_rows.length})</summary>
        <div className="schema-sample-table-wrapper">
          <table className="schema-sample-table">
            <thead>
              <tr>
                {preview.columns.map((col) => (
                  <th key={col.name}>{col.name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.sample_rows.map((row, i) => (
                <tr key={i}>
                  {preview.columns.map((col) => (
                    <td key={col.name}>{String(row[col.name] ?? '')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <div className="schema-context-note">
        <label className="schema-context-note-label" htmlFor="context-note">
          Dataset description <span className="schema-context-note-optional">(optional)</span>
        </label>
        <textarea
          id="context-note"
          className="schema-context-note-input"
          placeholder='e.g. "amt_2 is refund amount in USD"'
          rows={2}
          value={contextNote}
          onChange={(e) => setContextNote(e.target.value)}
        />
      </div>

      <div className="schema-preview-actions">
        <button
          className="schema-confirm-btn"
          onClick={() => onConfirm(preview.preview_token, contextNote)}
        >
          Confirm &amp; Load Data
        </button>
        <button className="schema-cancel-btn" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  )
}
