import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
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
  vi.useRealTimers()
})

describe('useThinkingStream', () => {
  it('reveals the trace agent-by-agent for a slow stream', async () => {
    vi.useFakeTimers()
    vi.mocked(streamAskQuestion).mockImplementation(async function* () {
      yield { type: 'step', stage: 'planner', detail: { ambiguity_score: 0.2 } }
      await delay(150)
      yield { type: 'step', stage: 'sql_generator', detail: { explanation: 'x' } }
      await delay(200)
      yield { type: 'done', payload: ANSWER }
    })

    const { result } = renderHook(() => useThinkingStream())

    let promise!: Promise<AskResponse>
    act(() => {
      promise = result.current.run('How many orders?')
    })

    // Reveal timer fires at 300ms, before the 350ms-away `done` event. Fake
    // timers drive both the reveal threshold and the mock stream's delays
    // deterministically, so there is no real-clock race here.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(310)
    })
    expect(result.current.trace?.steps.length).toBeGreaterThan(0)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100)
    })
    const resolved = await promise
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
