import { useRef, useState } from 'react'
import { SchemaPreview } from './SchemaPreview'
import { uploadPreview, uploadPreviewFromUrl, uploadConfirm, type UploadPreviewResponse } from '../api/uploadApi'

export type UploadState =
  | { phase: 'idle' }
  | { phase: 'uploading'; fileName: string }
  | { phase: 'url-loading' }
  | { phase: 'preview'; preview: UploadPreviewResponse }
  | { phase: 'loading' }
  | { phase: 'ready'; sessionId: string; rowCount: number; tableName: string }
  | { phase: 'tearing-down' }
  | { phase: 'error'; message: string }

interface UploadZoneProps {
  state: UploadState
  onStateChange: (state: UploadState) => void
  currentSessionId?: string
  onClearSession?: () => Promise<void>
}

export function UploadZone({ state, onStateChange, currentSessionId, onClearSession }: UploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [urlInput, setUrlInput] = useState('')

  async function handleFile(file: File) {
    const ext = file.name.toLowerCase().split('.').pop()
    if (ext !== 'csv' && ext !== 'json') {
      onStateChange({ phase: 'error', message: 'Only .csv and .json files are supported.' })
      return
    }

    onStateChange({ phase: 'uploading', fileName: file.name })

    try {
      const preview = await uploadPreview(file)
      onStateChange({ phase: 'preview', preview })
    } catch (err) {
      onStateChange({
        phase: 'error',
        message: err instanceof Error ? err.message : 'Upload failed',
      })
    }
  }

  async function handleUrlSubmit() {
    const url = urlInput.trim()
    if (!url) return

    let parsed: URL
    try {
      parsed = new URL(url)
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        onStateChange({ phase: 'error', message: 'Only HTTP and HTTPS URLs are supported.' })
        return
      }
    } catch {
      onStateChange({ phase: 'error', message: 'Invalid URL. Please enter a valid HTTP or HTTPS URL.' })
      return
    }

    onStateChange({ phase: 'url-loading' })

    try {
      const preview = await uploadPreviewFromUrl(url)
      onStateChange({ phase: 'preview', preview })
      setUrlInput('')
    } catch (err) {
      onStateChange({
        phase: 'error',
        message: err instanceof Error ? err.message : 'URL fetch failed',
      })
    }
  }

  function handleUrlKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      handleUrlSubmit()
    }
  }

  async function handleConfirm(previewToken: string, contextNote: string) {
    onStateChange({ phase: 'loading' })

    try {
      const result = await uploadConfirm(previewToken, contextNote, currentSessionId)
      onStateChange({
        phase: 'ready',
        sessionId: result.session_id,
        rowCount: result.row_count,
        tableName: result.table_name,
      })
    } catch (err) {
      onStateChange({
        phase: 'error',
        message: err instanceof Error ? err.message : 'Failed to load data',
      })
    }
  }

  function handleCancel() {
    onStateChange({ phase: 'idle' })
  }

  async function handleReplace() {
    if (onClearSession) {
      onStateChange({ phase: 'tearing-down' })
      await onClearSession()
    }
    onStateChange({ phase: 'idle' })
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
  }

  if (state.phase === 'idle') {
    return (
      <div className="upload-section">
        <div
          className="upload-zone"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.json"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleFile(file)
            }}
          />
          <div className="upload-zone-content">
            <div className="upload-zone-icon">CSV / JSON</div>
            <p className="upload-zone-title">Upload your own data</p>
            <p className="upload-zone-hint">Click or drop a CSV or JSON file to begin</p>
          </div>
        </div>
        <div className="upload-divider">
          <span className="upload-divider-text">or paste a URL</span>
        </div>
        <div className="upload-url-row">
          <input
            className="upload-url-input"
            type="text"
            placeholder="https://example.com/data.csv"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={handleUrlKeyDown}
          />
          <button
            className="upload-url-btn"
            onClick={handleUrlSubmit}
            disabled={!urlInput.trim()}
          >
            Fetch
          </button>
        </div>
      </div>
    )
  }

  if (state.phase === 'uploading') {
    return (
      <div className="upload-zone uploading">
        <p>Uploading <strong>{state.fileName}</strong>...</p>
      </div>
    )
  }

  if (state.phase === 'url-loading') {
    return (
      <div className="upload-zone uploading">
        <p>Fetching data from URL...</p>
      </div>
    )
  }

  if (state.phase === 'preview') {
    return (
      <SchemaPreview
        preview={state.preview}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    )
  }

  if (state.phase === 'loading') {
    return (
      <div className="upload-zone uploading">
        <p>Loading data into database...</p>
      </div>
    )
  }

  if (state.phase === 'ready') {
    return (
      <div className="upload-zone ready">
        <p>
          Uploaded <strong>{state.tableName}</strong> — {state.rowCount.toLocaleString()} rows loaded.
          Your questions will be answered using this dataset.
        </p>
        <button
          className="upload-reset-btn"
          onClick={handleReplace}
        >
          Upload a different file
        </button>
      </div>
    )
  }

  if (state.phase === 'tearing-down') {
    return (
      <div className="upload-zone uploading">
        <p>Clearing current session...</p>
      </div>
    )
  }

  if (state.phase === 'error') {
    return (
      <div className="upload-zone error">
        <p className="upload-error-text">{state.message}</p>
        <button
          className="upload-reset-btn"
          onClick={() => onStateChange({ phase: 'idle' })}
        >
          Try again
        </button>
      </div>
    )
  }

  return null
}