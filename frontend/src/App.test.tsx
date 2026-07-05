import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import type { AskResponse } from './types/api'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('App', () => {
  it('renders the heading', () => {
    render(<App />)
    expect(screen.getByText('Querio')).toBeInTheDocument()
  })

  it('renders the chat thread and input', () => {
    render(<App />)
    expect(screen.getByPlaceholderText('Ask a question...')).toBeInTheDocument()
  })

  it('sends a question and displays the answer', async () => {
    const answer: AskResponse = {
      type: 'answer',
      answer: 'Total orders: 100.',
      chart: null,
      sql: { sql: 'SELECT COUNT(*) FROM orders', explanation: 'count' },
      conversation_id: null,
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(answer), { status: 200 }),
    )

    render(<App />)
    const input = screen.getByPlaceholderText('Ask a question...')
    await userEvent.type(input, 'How many orders?{enter}')

    await waitFor(() => {
      expect(screen.getByText('Total orders: 100.')).toBeInTheDocument()
    })
  })

  it('sends a question and displays clarifying question', async () => {
    const clarify: AskResponse = {
      type: 'clarifying_question',
      question: 'Which metric?',
      options: ['count', 'list'],
      conversation_id: 'conv-1',
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(clarify), { status: 200 }),
    )

    render(<App />)
    const input = screen.getByPlaceholderText('Ask a question...')
    await userEvent.type(input, 'Show me customers{enter}')

    await waitFor(() => {
      expect(screen.getByText('Which metric?')).toBeInTheDocument()
    })
  })

  it('handles the full clarification flow: clarify then answer', async () => {
    const clarify: AskResponse = {
      type: 'clarifying_question',
      question: 'Which metric?',
      options: ['count', 'list'],
      conversation_id: 'conv-1',
    }
    const answer: AskResponse = {
      type: 'answer',
      answer: 'Count: 50.',
      chart: null,
      sql: null,
      conversation_id: 'conv-1',
    }

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(clarify), { status: 200 }))
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(answer), { status: 200 }))

    render(<App />)

    // Step 1: Ask a question
    const input = screen.getByPlaceholderText('Ask a question...')
    await userEvent.type(input, 'Show me customers{enter}')

    await waitFor(() => {
      expect(screen.getByText('Which metric?')).toBeInTheDocument()
    })

    // Step 2: Click a clarification option
    fireEvent.click(screen.getByRole('button', { name: 'count' }))

    await waitFor(() => {
      expect(screen.getByText('Count: 50.')).toBeInTheDocument()
    })

    // Verify the second API call included conversation_id and clarification_answer
    const secondCallBody = JSON.parse(fetchMock.mock.calls[1]?.[1]?.body as string)
    expect(secondCallBody).toHaveProperty('conversation_id', 'conv-1')
    expect(secondCallBody).toHaveProperty('clarification_answer', 'count')
  })

  it('shows error state when API fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    render(<App />)
    const input = screen.getByPlaceholderText('Ask a question...')
    await userEvent.type(input, 'How many?{enter}')

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
  })
})
