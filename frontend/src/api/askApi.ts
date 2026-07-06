import type { AskResponse } from '../types/api'
import { getMockResponse } from '../test/mockData'

const BASE_URL = '/api/ask'
const USE_MOCK = import.meta.env.VITE_MOCK === 'true' || import.meta.env.MODE === 'test'

export async function askQuestion(
  question: string,
  conversation_id?: string,
  clarification_answer?: string,
): Promise<AskResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 50))
    return getMockResponse(question, conversation_id, clarification_answer)
  }

  const body: Record<string, string> = { question }

  if (conversation_id !== undefined) {
    body.conversation_id = conversation_id
  }
  if (clarification_answer !== undefined && conversation_id !== undefined) {
    body.clarification_answer = clarification_answer
  }

  const response = await fetch(BASE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`)
  }

  return response.json() as Promise<AskResponse>
}
