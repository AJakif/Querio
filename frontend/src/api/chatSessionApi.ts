import type {
  ChatSessionResponse,
  ChatSessionHistoryResponse,
  ChatSessionSummaryResponse,
} from '../types/api'

const BASE_URL = '/api/session/chat'
const USE_MOCK = import.meta.env.VITE_MOCK === 'true' || import.meta.env.MODE === 'test'

// ---------------------------------------------------------------------------
// Mock data (test / VITE_MOCK mode)
// ---------------------------------------------------------------------------

export const MOCK_SESSION_ID = 'mock-chat-session-id'

export function getMockChatSession(): ChatSessionResponse {
  return {
    chat_session_id: MOCK_SESSION_ID,
    account_username: null,
    upload_session_id: null,
    created_at: '2026-07-19T10:00:00Z',
    updated_at: '2026-07-19T10:00:00Z',
  }
}

export function getMockChatSessionHistory(): ChatSessionHistoryResponse {
  return {
    session: getMockChatSession(),
    turns: [
      {
        turn_index: 0,
        question: 'How many orders?',
        answer: {
          type: 'answer',
          answer: 'There are **12,458** orders in the database.',
          chart: null,
          sql: { sql: 'SELECT COUNT(*) FROM orders', explanation: 'Count all orders.' },
          conversation_id: null,
        },
        created_at: '2026-07-19T10:01:00Z',
      },
    ],
  }
}

export function getMockChatSessionList(): ChatSessionSummaryResponse[] {
  return [
    {
      chat_session_id: MOCK_SESSION_ID,
      account_username: null,
      created_at: '2026-07-19T10:00:00Z',
      updated_at: '2026-07-19T10:01:00Z',
      turn_count: 1,
      preview_question: 'How many orders?',
    },
    {
      chat_session_id: 'mock-chat-session-id-2',
      account_username: null,
      created_at: '2026-07-18T09:00:00Z',
      updated_at: '2026-07-18T09:30:00Z',
      turn_count: 3,
      preview_question: 'Total revenue?',
    },
  ]
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * POST /api/session/chat — create a new chat session.
 * Returns 201 with ChatSessionResponse.
 */
export async function createChatSession(
  accountUsername?: string,
  uploadSessionId?: string,
): Promise<ChatSessionResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 10))
    return getMockChatSession()
  }

  const body: Record<string, string> = {}
  if (accountUsername !== undefined) body.account_username = accountUsername
  if (uploadSessionId !== undefined) body.upload_session_id = uploadSessionId

  const response = await fetch(BASE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Failed to create chat session: ${response.status}`)
  }

  return response.json() as Promise<ChatSessionResponse>
}

/**
 * GET /api/session/chat/{chat_session_id} — load a session with all stored turns.
 * Returns ChatSessionHistoryResponse or throws a SessionNotFoundError (404).
 */
export class SessionNotFoundError extends Error {
  constructor(id: string) {
    super(`Chat session not found: ${id}`)
    this.name = 'SessionNotFoundError'
  }
}

export async function getChatSession(chatSessionId: string): Promise<ChatSessionHistoryResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 10))
    if (chatSessionId === MOCK_SESSION_ID) return getMockChatSessionHistory()
    throw new SessionNotFoundError(chatSessionId)
  }

  const response = await fetch(`${BASE_URL}/${encodeURIComponent(chatSessionId)}`)

  if (response.status === 404) {
    throw new SessionNotFoundError(chatSessionId)
  }

  if (!response.ok) {
    throw new Error(`Failed to load chat session: ${response.status}`)
  }

  return response.json() as Promise<ChatSessionHistoryResponse>
}

/**
 * GET /api/session/chat?account_username=... — list sessions for an account.
 * When no account_username is supplied, returns all sessions (no-auth POC path).
 */
export async function listChatSessions(
  accountUsername?: string,
): Promise<ChatSessionSummaryResponse[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 10))
    return getMockChatSessionList()
  }

  const params = new URLSearchParams()
  if (accountUsername !== undefined) params.set('account_username', accountUsername)

  const url = params.size > 0 ? `${BASE_URL}?${params.toString()}` : BASE_URL
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to list chat sessions: ${response.status}`)
  }

  return response.json() as Promise<ChatSessionSummaryResponse[]>
}
