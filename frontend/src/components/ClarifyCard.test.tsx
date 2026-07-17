import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ClarifyCard } from './ClarifyCard'
import type { ClarifyResponse } from '../types/api'

const SAMPLE_MESSAGE: ClarifyResponse = {
  type: 'clarify',
  statement:
    'This dataset covers orders, customers, products — it doesn\'t include "churn": that concept isn\'t present in any table or column.',
  unresolved_terms: ['churn'],
  alternatives: [
    { label: 'Total price per month', question: 'What is the total price per month?' },
    { label: 'Average review score by order status', question: 'What is the average review score by order status?' },
  ],
  add_data: true,
}

describe('ClarifyCard', () => {
  it('renders the plain-language statement', () => {
    render(<ClarifyCard message={SAMPLE_MESSAGE} />)
    expect(screen.getByTestId('clarify-statement')).toHaveTextContent('churn')
  })

  it('renders at least 2 proxy alternative buttons', () => {
    render(<ClarifyCard message={SAMPLE_MESSAGE} />)
    const btns = screen.getAllByTestId('proxy-btn')
    expect(btns.length).toBeGreaterThanOrEqual(2)
    expect(btns[0]).toHaveTextContent('Total price per month')
    expect(btns[1]).toHaveTextContent('Average review score by order status')
  })

  it('calls onSend with the proxy question when a button is clicked', () => {
    const onSend = vi.fn()
    render(<ClarifyCard message={SAMPLE_MESSAGE} onSend={onSend} />)
    fireEvent.click(screen.getAllByTestId('proxy-btn')[0]!)
    expect(onSend).toHaveBeenCalledWith('What is the total price per month?')
  })

  it('renders the add-data escape hatch button', () => {
    render(<ClarifyCard message={SAMPLE_MESSAGE} />)
    expect(screen.getByTestId('add-data-btn')).toBeInTheDocument()
  })

  it('calls onAddData when the add-data button is clicked', () => {
    const onAddData = vi.fn()
    render(<ClarifyCard message={SAMPLE_MESSAGE} onAddData={onAddData} />)
    fireEvent.click(screen.getByTestId('add-data-btn'))
    expect(onAddData).toHaveBeenCalledOnce()
  })
})
