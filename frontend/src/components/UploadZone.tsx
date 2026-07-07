import { useRef } from 'react'
import { SchemaPreview } from './SchemaPreview'
import { uploadPreview, uploadConfirm, type UploadPreviewResponse } from '../api/uploadApi'

export type UploadState =
  | { phase: 'idle' }
  | { phase: 'uploading'; fileName: string }
  | { phase: 'preview'; preview: UploadPreviewResponse }
  | { phase: 'loading' }
  | { phase: 'ready'; sessionId: string; rowCount: number; tableName: string }
  | { phase: 'error'; message: string }

interface UploadZoneProps {
  state: UploadState
  onStateChange: (state: UploadState) => void
}

export function UploadZone({ state, onStateChange }: UploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  async function handleConfirm(previewToken: string) {
    onStateChange({ phase: 'loading' })

    try {
      const result = await uploadConfirm(previewToken)
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
    )
  }

  if (state.phase === 'uploading') {
    return (
      <div className="upload-zone uploading">
        <p>Uploading <strong>{state.fileName}</strong>...</p>
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
          onClick={() => onStateChange({ phase: 'idle' })}
        >
          Upload a different file
        </button>
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
