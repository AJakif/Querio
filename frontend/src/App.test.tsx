import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

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
    render(<App />)
    const input = screen.getByPlaceholderText('Ask a question...')
    await userEvent.type(input, 'How many orders?{enter}')

    await waitFor(() => {
      expect(screen.getByText((content) => content.includes('12,458'))).toBeInTheDocument()
    })
  })

  it('sends a question and displays clarifying question', async () => {
    render(<App />)
    const input = screen.getByPlaceholderText('Ask a question...')
    await userEvent.type(input, 'Show me customers{enter}')

    await waitFor(() => {
      expect(screen.getByText((content) => content.includes('Which attribute'))).toBeInTheDocument()
    })
  })

  it('handles the full clarification flow: clarify then answer', async () => {
    render(<App />)

    const input = screen.getByPlaceholderText('Ask a question...')
    await userEvent.type(input, 'Show me customers{enter}')

    await waitFor(() => {
      expect(screen.getByText((content) => content.includes('Which attribute'))).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'count' }))

    await waitFor(() => {
      expect(screen.getByText((content) => content.includes('9,940 customers'))).toBeInTheDocument()
    })
  })
})
