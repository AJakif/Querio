import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatThread } from './ChatThread'
import type { AskResponse, AnswerResponse, ClarifyingQuestionResponse } from '../types/api'

const answerMsg: AnswerResponse = {
  type: 'answer',
  answer: 'Total is 100.',
  chart: null,
  sql: null,
  conversation_id: null,
}

const clarifyMsg: ClarifyingQuestionResponse = {
  type: 'clarifying_question',
  question: 'Which metric?',
  options: ['count', 'sum'],
  conversation_id: 'conv-1',
}

describe('ChatThread', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders initial messages', () => {
    const messages: AskResponse[] = [answerMsg]
    render(<ChatThread messages={messages} onSend={vi.fn()} />)
    expect(screen.getByText('Total is 100.')).toBeInTheDocument()
  })

  it('calls onSend when user types and submits', async () => {
    const onSend = vi.fn()
    render(<ChatThread messages={[]} onSend={onSend} />)
    const input = screen.getByPlaceholderText(/ask a question/i)
    await userEvent.type(input, 'How many orders?')
    fireEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(onSend).toHaveBeenCalledWith('How many orders?')
  })

  it('clears input after sending', async () => {
    const onSend = vi.fn()
    render(<ChatThread messages={[]} onSend={onSend} />)
    const input = screen.getByPlaceholderText(/ask a question/i) as HTMLInputElement
    await userEvent.type(input, 'Test question')
    fireEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(input.value).toBe('')
  })

  it('does not send empty messages', async () => {
    const onSend = vi.fn()
    render(<ChatThread messages={[]} onSend={onSend} />)
    fireEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(onSend).not.toHaveBeenCalled()
  })

  it('renders clarifying question with options', () => {
    const messages: AskResponse[] = [clarifyMsg]
    render(<ChatThread messages={messages} onSend={vi.fn()} />)
    expect(screen.getByText('Which metric?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'count' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'sum' })).toBeInTheDocument()
  })

  it('calls onClarify when an option is clicked', () => {
    const onClarify = vi.fn()
    const messages: AskResponse[] = [clarifyMsg]
    render(<ChatThread messages={messages} onSend={vi.fn()} onClarify={onClarify} />)
    fireEvent.click(screen.getByRole('button', { name: 'count' }))
    expect(onClarify).toHaveBeenCalledWith('conv-1', 'count')
  })

  it('disables only non-last clarifying question options', () => {
    const laterClarify: ClarifyingQuestionResponse = {
      type: 'clarifying_question',
      question: 'Which table?',
      options: ['orders', 'customers'],
      conversation_id: 'conv-2',
    }
    const messages: AskResponse[] = [clarifyMsg, laterClarify]
    render(<ChatThread messages={messages} onSend={vi.fn()} onClarify={vi.fn()} />)
    const firstButtons = screen.getAllByRole('button', { name: /count|sum/ })
    firstButtons.forEach((btn) => expect(btn).toBeDisabled())
    const secondButtons = screen.getAllByRole('button', { name: /orders|customers/ })
    secondButtons.forEach((btn) => expect(btn).not.toBeDisabled())
  })

  it('shows loading indicator when loading is true', () => {
    render(<ChatThread messages={[]} onSend={vi.fn()} loading={true} />)
    expect(screen.getByText(/thinking/i)).toBeInTheDocument()
  })

  it('shows error message when error is provided', () => {
    render(<ChatThread messages={[]} onSend={vi.fn()} error="Something went wrong" />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('sends on submit via Enter key', async () => {
    const onSend = vi.fn()
    render(<ChatThread messages={[]} onSend={onSend} />)
    const input = screen.getByPlaceholderText(/ask a question/i)
    await userEvent.type(input, 'Enter key submit{enter}')
    expect(onSend).toHaveBeenCalledWith('Enter key submit')
  })
})
