import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useThinkingStream } from './useThinkingStream'
import type { AskResponse } from '../types/api'

vi.mock('../api/askStreamApi', () => ({
  streamAskQuestion: vi.fn(),
}))

import { streamAskQuestion } from '../api/askStreamApi'

const ANSWER: AskResponse = {
  type: 'answer',
  answer: 'Done.',
  chart: null,
  sql: null,
  conversation_id: null,
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useThinkingStream', () => {
  it('reveals the trace agent-by-agent for a slow stream', async () => {
    vi.mocked(streamAskQuestion).mockImplementation(async function* () {
      yield { type: 'step', stage: 'planner', detail: { ambiguity_score: 0.2 } }
      await delay(150)
      yield { type: 'step', stage: 'sql_generator', detail: { explanation: 'x' } }
      await delay(200)
      yield { type: 'done', payload: ANSWER }
    })

    const { result } = renderHook(() => useThinkingStream())

    let promise: Promise<AskResponse>
    act(() => {
      promise = result.current.run('How many orders?')
    })

    await waitFor(() => expect(result.current.trace?.steps.length).toBeGreaterThan(0), { timeout: 1000 })

    const resolved = await act(async () => promise)
    expect(resolved).toEqual(ANSWER)
    expect(result.current.trace).toBeNull()
  })

  it('fires no animation for a response resolving under 300ms', async () => {
    vi.mocked(streamAskQuestion).mockImplementation(async function* () {
      yield { type: 'done', payload: ANSWER }
    })

    const { result } = renderHook(() => useThinkingStream())

    let resolved: AskResponse | undefined
    await act(async () => {
      resolved = await result.current.run('How many orders?')
    })

    expect(resolved).toEqual(ANSWER)
    expect(result.current.trace).toBeNull()
  })
})
