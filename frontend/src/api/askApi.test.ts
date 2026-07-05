import { describe, it, expect, vi, beforeEach } from 'vitest'
import { askQuestion } from './askApi'
import type { AskResponse } from '../types/api'

const BASE_URL = '/api/ask'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('askQuestion', () => {
  it('sends a question and returns the response', async () => {
    const mockResponse: AskResponse = {
      type: 'answer',
      answer: 'The answer is **42**.',
      chart: null,
      sql: { sql: 'SELECT 42', explanation: 'test' },
      conversation_id: null,
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockResponse), { status: 200 }),
    )

    const result = await askQuestion('What is the meaning of life?')

    expect(fetchMock).toHaveBeenCalledWith(BASE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: 'What is the meaning of life?' }),
    })
    expect(result).toEqual(mockResponse)
  })

  it('sends conversation_id and clarification_answer', async () => {
    const mockResponse: AskResponse = {
      type: 'answer',
      answer: 'Count is 10.',
      chart: null,
      sql: null,
      conversation_id: 'conv-123',
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockResponse), { status: 200 }),
    )

    const result = await askQuestion('count', 'conv-123', 'count')

    expect(result).toEqual(mockResponse)
  })

  it('sends clarification_answer only when conversation_id is also provided', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ type: 'clarifying_question', question: 'Which?', options: ['a'], conversation_id: 'c1' }), { status: 200 }),
    )

    await askQuestion('show customers', 'c1', 'list')

    const callArg = JSON.parse((fetchMock.mock.calls[0]?.[1]?.body as string) ?? '{}')
    expect(callArg).toEqual({
      question: 'show customers',
      conversation_id: 'c1',
      clarification_answer: 'list',
    })
  })

  it('throws on non-ok response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, { status: 500 }),
    )

    await expect(askQuestion('test')).rejects.toThrow()
  })

  it('throws on malformed JSON', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('not json', { status: 200 }),
    )

    await expect(askQuestion('test')).rejects.toThrow()
  })
})
