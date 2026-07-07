const BASE_URL = '/api/upload'

export interface ColumnStats {
  null_percentage: number
  min_value: number | null
  max_value: number | null
  mean_value: number | null
  top_values: { value: string; count: number }[] | null
}

export interface ColumnPreview {
  name: string
  inferred_type: string
  stats: ColumnStats
}

export interface UploadPreviewResponse {
  columns: ColumnPreview[]
  sample_rows: Record<string, unknown>[]
  total_rows: number
  preview_token: string
}

export interface UploadConfirmResponse {
  session_id: string
  table_name: string
  row_count: number
}

export async function uploadPreview(file: File): Promise<UploadPreviewResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${BASE_URL}/preview`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Upload failed with status ${response.status}`)
  }

  return response.json() as Promise<UploadPreviewResponse>
}

export async function uploadPreviewFromUrl(url: string): Promise<UploadPreviewResponse> {
  const response = await fetch(`${BASE_URL}/preview-from-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `URL fetch failed with status ${response.status}`)
  }

  return response.json() as Promise<UploadPreviewResponse>
}

export async function uploadConfirm(previewToken: string, contextNote?: string, currentSessionId?: string): Promise<UploadConfirmResponse> {
  const response = await fetch(`${BASE_URL}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      preview_token: previewToken,
      context_note: contextNote ?? '',
      current_session_id: currentSessionId ?? '',
    }),
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Confirm failed with status ${response.status}`)
  }

  return response.json() as Promise<UploadConfirmResponse>
}

export async function teardownSession(sessionId: string): Promise<void> {
  const response = await fetch(`/api/session/${encodeURIComponent(sessionId)}/teardown`, {
    method: 'POST',
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Session teardown failed with status ${response.status}`)
  }
}
