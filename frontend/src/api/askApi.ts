import type { AskResponse } from '../types/api'

const BASE_URL = '/api/ask'

export async function askQuestion(
  question: string,
  conversation_id?: string,
  clarification_answer?: string,
): Promise<AskResponse> {
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
