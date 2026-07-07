const BASE_URL = '/api/upload'

export interface ColumnPreview {
  name: string
  inferred_type: string
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

export async function uploadConfirm(previewToken: string): Promise<UploadConfirmResponse> {
  const response = await fetch(`${BASE_URL}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preview_token: previewToken }),
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Confirm failed with status ${response.status}`)
  }

  return response.json() as Promise<UploadConfirmResponse>
}
