import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ResultsPane } from './ResultsPane'
import type { AnswerResponse, AnswerSpec } from '../types/api'

describe('ResultsPane', () => {
  it('shows an empty state when no message is selected', () => {
    render(<ResultsPane message={null} />)
    expect(screen.getByTestId('results-pane-empty')).toBeInTheDocument()
  })

  it('renders the legacy answer text, chart, and SQL when no answer_spec is present', () => {
    const message: AnswerResponse = {
      type: 'answer',
      answer: 'Total is 100.',
      chart: {
        chart_type: 'bar',
        title: 'Orders by Month',
        data: [{ month: 'Jan', count: 10 }],
        x_key: 'month',
        y_key: 'count',
      },
      sql: { sql: 'SELECT 100', explanation: 'test query' },
      conversation_id: null,
    }
    render(<ResultsPane message={message} />)
    // The raw answer text stays in the chat-pane teaser (not duplicated here) —
    // this pane only adds the chart and SQL detail.
    expect(screen.getByText('Orders by Month')).toBeInTheDocument()
    expect(screen.getByText('SELECT 100')).toBeInTheDocument()
    expect(screen.getByText('test query')).toBeInTheDocument()
  })

  it('renders the AnswerCard when answer_spec is present', () => {
    const spec: AnswerSpec = {
      response_type: 'stat',
      headline: { value: '$13.6M', label: 'Net revenue', sign: 'neutral' },
      restatement: 'Net revenue for Q2 2024',
      chart_spec: null,
      suppression_reason: 'single-value; no chart needed',
      claims: [],
      followups: [],
      assumptions_ref: [],
      dropped_claim_count: 0,
    }
    const message: AnswerResponse = {
      type: 'answer',
      answer: 'Net revenue for Q2 2024',
      chart: null,
      sql: null,
      conversation_id: null,
      answer_spec: spec,
      badge_state: 'verified',
    }
    render(<ResultsPane message={message} />)
    expect(screen.getByTestId('answer-card')).toBeInTheDocument()
    expect(screen.getByTestId('headline-stat')).toBeInTheDocument()
  })
})
