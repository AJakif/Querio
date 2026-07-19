import type { AskResponse } from '../types/api'
import { askQuestion } from './askApi'

const STREAM_URL = '/api/ask/stream'
const USE_MOCK = import.meta.env.VITE_MOCK === 'true' || import.meta.env.MODE === 'test'

export interface StepEvent {
  type: 'step'
  stage: string
  detail: Record<string, unknown>
}

export type StreamEvent =
  | StepEvent
  | { type: 'done'; payload: AskResponse }
  | { type: 'error'; message: string }

/**
 * Streams the /ask pipeline over SSE, yielding a `step` event per completed agent
 * stage (real Planner/Validator/Aggregator data) and a final `done` event carrying
 * the same payload shape the non-streaming /ask endpoint returns.
 *
 * In test/mock mode this degrades to a single immediate `done` event backed by the
 * existing mock JSON responder — there is no mock SSE backend, and the mock resolves
 * well under the 300ms "no animation" threshold anyway, so the behavior is equivalent.
 */
export async function* streamAskQuestion(
  question: string,
  conversation_id?: string,
  clarification_answer?: string,
  session_id?: string,
  chat_session_id?: string,
): AsyncGenerator<StreamEvent> {
  if (USE_MOCK) {
    const payload = await askQuestion(question, conversation_id, clarification_answer, session_id, chat_session_id)
    yield { type: 'done', payload }
    return
  }

  const params = new URLSearchParams({ question })
  if (conversation_id !== undefined) params.set('conversation_id', conversation_id)
  if (clarification_answer !== undefined) params.set('clarification_answer', clarification_answer)
  if (session_id !== undefined) params.set('session_id', session_id)
  if (chat_session_id !== undefined) params.set('chat_session_id', chat_session_id)

  const response = await fetch(`${STREAM_URL}?${params.toString()}`, {
    headers: { Accept: 'text/event-stream' },
  })

  if (!response.ok || !response.body) {
    throw new Error(`Stream request failed with status ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        const rawEvent = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        const parsed = _parseSseFrame(rawEvent)
        if (parsed) yield parsed
        boundary = buffer.indexOf('\n\n')
      }
    }
  } finally {
    reader.releaseLock()
  }
}

function _parseSseFrame(rawEvent: string): StreamEvent | null {
  let eventName = 'message'
  let data = ''
  for (const line of rawEvent.split('\n')) {
    if (line.startsWith('event: ')) {
      eventName = line.slice('event: '.length)
    } else if (line.startsWith('data: ')) {
      data = line.slice('data: '.length)
    }
  }
  if (!data) return null

  const parsed: unknown = JSON.parse(data)
  if (eventName === 'step') {
    const { stage, detail } = parsed as { stage: string; detail: Record<string, unknown> }
    return { type: 'step', stage, detail }
  }
  if (eventName === 'done') {
    return { type: 'done', payload: parsed as AskResponse }
  }
  if (eventName === 'error') {
    const { message } = parsed as { message: string }
    return { type: 'error', message }
  }
  return null
}
