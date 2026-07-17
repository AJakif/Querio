import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UploadZone, type UploadState } from './UploadZone'

const readyWithSuggestions: UploadState = {
  phase: 'ready',
  sessionId: 'sess-1',
  rowCount: 42,
  tableName: 'uploaded_data',
  joinKeyColumn: 'customer_id',
  joinKeyTable: 'fct_orders',
  suggestedQuestions: [
    'How many records in uploaded_data match fct_orders on customer_id?',
    'Show a combined view of uploaded_data and fct_orders joined on customer_id.',
  ],
}

const readyWithoutSuggestions: UploadState = {
  phase: 'ready',
  sessionId: 'sess-2',
  rowCount: 10,
  tableName: 'uploaded_data',
  joinKeyColumn: null,
  joinKeyTable: null,
  suggestedQuestions: [],
}

describe('UploadZone suggestion chips', () => {
  it('renders suggestion chips referencing the detected join key', () => {
    render(<UploadZone state={readyWithSuggestions} onStateChange={vi.fn()} />)
    expect(screen.getByText('customer_id')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /How many records in uploaded_data match fct_orders on customer_id/ })
    ).toBeInTheDocument()
  })

  it('submits a suggestion as a real question when tapped', async () => {
    const onSuggestionSelect = vi.fn()
    render(
      <UploadZone
        state={readyWithSuggestions}
        onStateChange={vi.fn()}
        onSuggestionSelect={onSuggestionSelect}
      />
    )
    const chip = screen.getByRole('button', { name: /Show a combined view/ })
    await userEvent.click(chip)
    expect(onSuggestionSelect).toHaveBeenCalledWith(
      'Show a combined view of uploaded_data and fct_orders joined on customer_id.'
    )
  })

  it('renders no suggestion chips when no join key was detected', () => {
    render(<UploadZone state={readyWithoutSuggestions} onStateChange={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /How many records/ })).not.toBeInTheDocument()
  })
})
