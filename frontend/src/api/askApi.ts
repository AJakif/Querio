import type { AskRequest, AskResponse } from '../types/api'
import { getMockResponse, getMockConfirmResponse } from '../test/mockData'

const BASE_URL = '/api/ask'
const USE_MOCK = import.meta.env.VITE_MOCK === 'true' || import.meta.env.MODE === 'test'

export async function askQuestion(
  question: string,
  conversation_id?: string,
  clarification_answer?: string,
  session_id?: string,
  chat_session_id?: string,
): Promise<AskResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 50))
    return getMockResponse(question, conversation_id, clarification_answer)
  }

  const body: AskRequest = { question }

  if (conversation_id !== undefined) {
    body.conversation_id = conversation_id
  }
  if (clarification_answer !== undefined && conversation_id !== undefined) {
    body.clarification_answer = clarification_answer
  }
  if (session_id !== undefined) {
    body.session_id = session_id
  }
  if (chat_session_id !== undefined) {
    body.chat_session_id = chat_session_id
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

export async function confirmAssumptions(
  conversation_id: string,
  amendments: { term: string; resolution: string }[],
): Promise<AskResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 50))
    return getMockConfirmResponse()
  }

  const response = await fetch(`${BASE_URL}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id, amendments }),
  })

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`)
  }

  return response.json() as Promise<AskResponse>
}
