import { describe, it, expect } from 'vitest'
import { askQuestion } from './askApi'

describe('askQuestion with mock', () => {
  it('returns answer for a well-formed question', async () => {
    const result = await askQuestion('How many orders?')
    expect(result.type).toBe('answer')
    if (result.type === 'answer') {
      expect(result.answer).toBeTruthy()
      expect(result.sql).toBeTruthy()
    }
  })

  it('returns clarifying question for vague input', async () => {
    const result = await askQuestion('Show me customers')
    expect(result.type).toBe('clarifying_question')
    if (result.type === 'clarifying_question') {
      expect(result.question).toContain('count')
      expect(result.options.length).toBeGreaterThan(0)
      expect(result.conversation_id).toBeTruthy()
    }
  })

  it('returns answer when providing clarification answer', async () => {
    const result = await askQuestion('customers', 'mock-conv-1', 'count')
    expect(result.type).toBe('answer')
    if (result.type === 'answer') {
      expect(result.answer).toContain('count')
      expect(result.conversation_id).toBe('mock-conv-1')
    }
  })

  it('handles "vague" as ambiguous question', async () => {
    const result = await askQuestion('vague question')
    expect(result.type).toBe('clarifying_question')
  })
})
