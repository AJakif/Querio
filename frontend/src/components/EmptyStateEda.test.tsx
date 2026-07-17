import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EmptyStateEda } from './EmptyStateEda'
import * as schemaApi from '../api/schemaApi'
import type { SchemaSummaryResponse } from '../types/api'

const fixtureSummary: SchemaSummaryResponse = {
  table_name: 'fct_orders',
  row_count: 99441,
  date_span_start: '2016-09-04',
  date_span_end: '2018-10-17',
  key_dimension_count: 3,
  headline_label: 'Total total_payment_value',
  headline_value: 15843553.24,
  examples: [
    { question: 'How many fct_orders are there in total?', answer_shape: 'number', hint: 'Returns a single number.' },
    { question: 'What is the total total_payment_value across all fct_orders?', answer_shape: 'number', hint: 'Returns a single number.' },
    { question: 'What is the total total_payment_value by order_status?', answer_shape: 'chart', hint: 'Returns a chart broken down by order_status.' },
    { question: 'What are the top 10 fct_orders by total_payment_value?', answer_shape: 'list', hint: 'Returns a list of the top matching rows.' },
  ],
}

describe('EmptyStateEda', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders real stats and grounded example questions from the fetched schema summary', async () => {
    vi.spyOn(schemaApi, 'fetchSchemaSummary').mockResolvedValue(fixtureSummary)

    render(<EmptyStateEda onSend={vi.fn()} />)

    expect(await screen.findByText('99,441 rows')).toBeInTheDocument()
    expect(screen.getByText('2016-09-04 to 2018-10-17')).toBeInTheDocument()
    expect(screen.getByText('3 key dimensions')).toBeInTheDocument()
    expect(screen.getByText(/Total total_payment_value/)).toBeInTheDocument()
    expect(screen.getByText('What is the total total_payment_value by order_status?')).toBeInTheDocument()
  })

  it('submits an example question through onSend when tapped', async () => {
    vi.spyOn(schemaApi, 'fetchSchemaSummary').mockResolvedValue(fixtureSummary)
    const onSend = vi.fn()

    render(<EmptyStateEda onSend={onSend} />)

    const button = await screen.findByText('How many fct_orders are there in total?')
    await userEvent.click(button)

    expect(onSend).toHaveBeenCalledWith('How many fct_orders are there in total?')
  })

  it('refetches the summary when sessionId changes (dataset switch)', async () => {
    const spy = vi
      .spyOn(schemaApi, 'fetchSchemaSummary')
      .mockResolvedValueOnce(fixtureSummary)
      .mockResolvedValueOnce({ ...fixtureSummary, table_name: 'uploaded_data', row_count: 42 })

    const { rerender } = render(<EmptyStateEda onSend={vi.fn()} sessionId={undefined} />)
    await waitFor(() => expect(spy).toHaveBeenCalledWith(undefined))

    rerender(<EmptyStateEda onSend={vi.fn()} sessionId="session-123" />)

    await waitFor(() => expect(spy).toHaveBeenCalledWith('session-123'))
    expect(await screen.findByText('42 rows')).toBeInTheDocument()
  })
})
