import type { SchemaSummaryResponse } from '../types/api'
import { getMockSchemaSummary } from '../test/mockData'

const BASE_URL = '/api/schema'
const USE_MOCK = import.meta.env.VITE_MOCK === 'true' || import.meta.env.MODE === 'test'

export async function fetchSchemaSummary(sessionId?: string): Promise<SchemaSummaryResponse> {
  if (USE_MOCK) {
    return getMockSchemaSummary()
  }

  const url = sessionId
    ? `${BASE_URL}/summary?session_id=${encodeURIComponent(sessionId)}`
    : `${BASE_URL}/summary`

  const response = await fetch(url)

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Schema summary request failed with status ${response.status}`)
  }

  return response.json() as Promise<SchemaSummaryResponse>
}
