import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
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

let originalMatchMedia: typeof window.matchMedia

beforeEach(() => {
  originalMatchMedia = window.matchMedia
  window.matchMedia = ((query: string) =>
    ({
      matches: query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList) as typeof window.matchMedia
})

afterEach(() => {
  window.matchMedia = originalMatchMedia
  vi.restoreAllMocks()
})

describe('useThinkingStream with prefers-reduced-motion', () => {
  it('never reveals the step-by-step trace even for a slow stream', async () => {
    vi.mocked(streamAskQuestion).mockImplementation(async function* () {
      yield { type: 'step', stage: 'planner', detail: { ambiguity_score: 0.2 } }
      await delay(400)
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
