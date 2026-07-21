import { useState } from 'react'
import { UploadZone, type UploadState } from './UploadZone'

interface DataBarProps {
  state: UploadState
  onStateChange: (state: UploadState) => void
  currentSessionId?: string
  onClearSession?: () => Promise<void>
  onSuggestionSelect?: (question: string) => void
}

function summaryFor(state: UploadState): string {
  switch (state.phase) {
    case 'idle':
      return 'Add your own data (CSV, JSON, or a URL)'
    case 'uploading':
      return `Uploading ${state.fileName}...`
    case 'url-loading':
      return 'Fetching data from URL...'
    case 'preview':
      return 'Review detected schema'
    case 'loading':
      return 'Loading data into database...'
    case 'ready':
      return `${state.tableName} · ${state.rowCount.toLocaleString()} rows loaded`
    case 'tearing-down':
      return 'Clearing current session...'
    case 'error':
      return 'Upload failed — click to retry'
    default:
      return 'Add your own data'
  }
}

/**
 * Collapsed by default so the upload flow doesn't dominate the page — expands
 * on click to reveal the full drop-zone / schema-preview / confirmation UI.
 */
export function DataBar({ state, onStateChange, currentSessionId, onClearSession, onSuggestionSelect }: DataBarProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="data-bar">
      <button
        type="button"
        className="data-bar-toggle"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        <span className="data-bar-toggle__label">{summaryFor(state)}</span>
        <span className="data-bar-toggle__caret" aria-hidden="true">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="data-bar-content">
          <UploadZone
            state={state}
            onStateChange={onStateChange}
            currentSessionId={currentSessionId}
            onClearSession={onClearSession}
            onSuggestionSelect={onSuggestionSelect}
          />
        </div>
      )}
    </div>
  )
}
