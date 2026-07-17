import { useCallback, useState } from 'react'
import { streamAskQuestion, type StepEvent } from '../api/askStreamApi'
import type { AskResponse } from '../types/api'

// Answers resolving faster than this render with no animation at all (no flash-then-vanish).
const REVEAL_THRESHOLD_MS = 300

export interface TraceState {
  steps: StepEvent[]
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/**
 * Drives the thinking-state SSE trace. Consumers get back the live `trace` (null
 * until it's worth showing) and an `run()` that resolves to the final answer/
 * clarification payload, matching the shape of the plain askQuestion() call.
 *
 * Gating logic: the trace is only ever revealed once REVEAL_THRESHOLD_MS elapses
 * without a `done` event. If the answer resolves first, or the user has
 * prefers-reduced-motion set, the trace never mounts and the final result renders
 * directly — this covers both the <300ms "no flash" case and the reduced-motion
 * "no step-by-step animation" case with one mechanism.
 */
export function useThinkingStream() {
  const [trace, setTrace] = useState<TraceState | null>(null)

  const run = useCallback(
    async (
      question: string,
      conversationId?: string,
      clarificationAnswer?: string,
      sessionId?: string,
    ): Promise<AskResponse> => {
      const steps: StepEvent[] = []
      let revealed = false

      const timer = prefersReducedMotion()
        ? null
        : setTimeout(() => {
            revealed = true
            setTrace({ steps: [...steps] })
          }, REVEAL_THRESHOLD_MS)

      try {
        for await (const evt of streamAskQuestion(question, conversationId, clarificationAnswer, sessionId)) {
          if (evt.type === 'step') {
            steps.push(evt)
            if (revealed) setTrace({ steps: [...steps] })
          } else if (evt.type === 'done') {
            const payload = evt.payload
            if (payload.type === 'answer') {
              payload._trace_steps = [...steps]
            }
            return payload
          } else {
            throw new Error(evt.message)
          }
        }
        throw new Error('Stream ended without a result')
      } finally {
        if (timer) clearTimeout(timer)
        setTrace(null)
      }
    },
    [],
  )

  return { trace, run }
}
