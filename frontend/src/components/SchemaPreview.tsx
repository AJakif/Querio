import type { UploadPreviewResponse } from '../api/uploadApi'

interface SchemaPreviewProps {
  preview: UploadPreviewResponse
  onConfirm: (previewToken: string) => void
  onCancel: () => void
}

export function SchemaPreview({ preview, onConfirm, onCancel }: SchemaPreviewProps) {
  return (
    <div className="schema-preview">
      <h3 className="schema-preview-title">Schema Preview</h3>
      <p className="schema-preview-meta">
        {preview.total_rows.toLocaleString()} rows &middot; {preview.columns.length} columns
      </p>

      <table className="schema-table">
        <thead>
          <tr>
            <th>Column</th>
            <th>Inferred Type</th>
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
            </tr>
          ))}
        </tbody>
      </table>

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

      <div className="schema-preview-actions">
        <button
          className="schema-confirm-btn"
          onClick={() => onConfirm(preview.preview_token)}
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
