import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ChatBubble } from './ChatBubble'
import type { AnswerResponse, ClarifyingQuestionResponse, ConfirmFirstResponse } from '../types/api'

describe('ChatBubble — answer', () => {
  const answerMsg: AnswerResponse = {
    type: 'answer',
    answer: 'The result is **42**.',
    chart: null,
    sql: { sql: 'SELECT 42', explanation: 'test query' },
    conversation_id: null,
  }

  it('renders the answer text', () => {
    render(<ChatBubble message={answerMsg} />)
    const matches = screen.getAllByText((content) => content.includes('42'))
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  // SQL and chart detail no longer render inline in the chat bubble — they move
  // to the ResultsPane once this turn is selected (see ResultsPane.test.tsx).
  it('does not render SQL or chart detail inline', () => {
    const msgWithChart: AnswerResponse = {
      ...answerMsg,
      chart: {
        chart_type: 'bar',
        title: 'Orders by Month',
        data: [{ month: 'Jan', count: 10 }],
        x_key: 'month',
        y_key: 'count',
      },
    }
    render(<ChatBubble message={msgWithChart} />)
    expect(screen.queryByText('SELECT 42')).toBeNull()
    expect(screen.queryByText('Orders by Month')).toBeNull()
  })

  it('renders an answer bubble (not clarifier)', () => {
    const { container } = render(<ChatBubble message={answerMsg} />)
    expect(container.querySelector('[data-testid="answer-bubble"]')).toBeInTheDocument()
    expect(container.querySelector('[data-testid="clarifier-bubble"]')).toBeNull()
  })

  it('calls onSelect when clicked', () => {
    const onSelect = vi.fn()
    render(<ChatBubble message={answerMsg} onSelect={onSelect} />)
    fireEvent.click(screen.getByTestId('answer-bubble'))
    expect(onSelect).toHaveBeenCalled()
  })

  it('applies a selected class when isSelected is true', () => {
    render(<ChatBubble message={answerMsg} isSelected onSelect={vi.fn()} />)
    expect(screen.getByTestId('answer-bubble').className).toContain('answer-teaser--selected')
  })
})

describe('ChatBubble — clarifying question', () => {
  const clarifyMsg: ClarifyingQuestionResponse = {
    type: 'clarifying_question',
    question: 'Which attribute — count, list, or by region?',
    options: ['count', 'list', 'by region'],
    conversation_id: 'conv-1',
  }

  it('renders the clarifying question text', () => {
    render(<ChatBubble message={clarifyMsg} onOptionSelect={vi.fn()} />)
    expect(screen.getByText('Which attribute — count, list, or by region?')).toBeInTheDocument()
  })

  it('renders a clarifier bubble (distinct from answer)', () => {
    const { container } = render(<ChatBubble message={clarifyMsg} onOptionSelect={vi.fn()} />)
    expect(container.querySelector('[data-testid="clarifier-bubble"]')).toBeInTheDocument()
    expect(container.querySelector('[data-testid="answer-bubble"]')).toBeNull()
  })

  it('renders a clarifying label', () => {
    render(<ChatBubble message={clarifyMsg} onOptionSelect={vi.fn()} />)
    expect(screen.getByText(/clarification/i)).toBeInTheDocument()
  })

  it('renders all options as buttons', () => {
    render(<ChatBubble message={clarifyMsg} onOptionSelect={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'count' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'list' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'by region' })).toBeInTheDocument()
  })

  it('calls onOptionSelect with the option when clicked', () => {
    const onSelect = vi.fn()
    render(<ChatBubble message={clarifyMsg} onOptionSelect={onSelect} />)
    fireEvent.click(screen.getByRole('button', { name: 'list' }))
    expect(onSelect).toHaveBeenCalledWith('list')
  })

  it('disables options when disabled prop is true', () => {
    render(<ChatBubble message={clarifyMsg} onOptionSelect={vi.fn()} disabled={true} />)
    const buttons = screen.getAllByRole('button')
    buttons.forEach((btn) => {
      expect(btn).toBeDisabled()
    })
  })
})

describe('ChatBubble — confirm_first gate', () => {
  const confirmMsg: ConfirmFirstResponse = {
    type: 'confirm_first',
    conversation_id: 'confirm-abc',
    plan: {
      ambiguity_score: 0.9,
      assumptions: [
        { term: 'recent', resolution: 'last 30 days', alternatives: ['last 7 days'], close_call: true },
        { term: 'status', resolution: 'delivered', alternatives: [], close_call: false },
      ],
      unresolved_terms: [],
      interpretation: 'Showing recent delivered orders',
    },
    scan_cost: 0,
    gate_reason: 'ambiguity',
  }

  it('renders assumption chips for each assumption', () => {
    render(<ChatBubble message={confirmMsg} onConfirm={vi.fn()} />)
    expect(screen.getByTestId('chip-recent')).toBeInTheDocument()
    expect(screen.getByTestId('chip-status')).toBeInTheDocument()
  })

  it('confirm button calls onConfirm with no amendments when nothing edited', () => {
    const onConfirm = vi.fn()
    render(<ChatBubble message={confirmMsg} onConfirm={onConfirm} />)
    fireEvent.click(screen.getByTestId('confirm-button'))
    expect(onConfirm).toHaveBeenCalledWith('confirm-abc', [])
  })

  it('clicking a chip opens an editable input, and confirming after an edit sends the amendment', () => {
    const onConfirm = vi.fn()
    render(<ChatBubble message={confirmMsg} onConfirm={onConfirm} />)

    fireEvent.click(screen.getByTestId('chip-recent'))
    const input = screen.getByLabelText('Edit assumption: recent')
    fireEvent.change(input, { target: { value: 'last 7 days' } })
    fireEvent.click(screen.getByTestId('confirm-button'))

    expect(onConfirm).toHaveBeenCalledWith('confirm-abc', [{ term: 'recent', resolution: 'last 7 days' }])
  })
})
