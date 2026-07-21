import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { getPipelinePhrase, PipelineStatus } from './PipelineStatus'
import type { StepEvent } from '../api/askStreamApi'

const step = (stage: string, detail: Record<string, unknown> = {}): StepEvent => ({
  type: 'step',
  stage,
  detail,
})

describe('getPipelinePhrase', () => {
  it.each([
    {
      label: '0 steps',
      steps: [] as StepEvent[],
      expected: 'Understanding your question…',
    },
    {
      label: 'planner only',
      steps: [step('planner')],
      expected: 'Looking at your data…',
    },
    {
      label: 'sql_generator with FROM marts.fct_orders',
      steps: [step('planner'), step('sql_generator', { sql: 'SELECT * FROM marts.fct_orders LIMIT 10', explanation: '' })],
      expected: 'Looking at your fct_orders table…',
    },
    {
      label: 'sql_generator with no recognisable FROM',
      steps: [step('sql_generator', { sql: 'SELECT 1', explanation: '' })],
      expected: 'Looking at your data…',
    },
    {
      label: 'validator present',
      steps: [step('planner'), step('sql_generator', { sql: 'SELECT 1' }), step('validator')],
      expected: 'Running the query…',
    },
    {
      label: 'aggregator present',
      steps: [step('planner'), step('sql_generator', { sql: 'SELECT 1' }), step('validator'), step('aggregator')],
      expected: 'Checking the numbers…',
    },
  ])('$label → "$expected"', ({ steps, expected }) => {
    expect(getPipelinePhrase(steps)).toBe(expected)
  })
})

describe('PipelineStatus component', () => {
  it('renders the pulsing dot and phrase text', () => {
    render(<PipelineStatus steps={[step('planner')]} />)
    expect(screen.getByTestId('pipeline-status')).toBeInTheDocument()
    expect(screen.getByText('Looking at your data…')).toBeInTheDocument()
    // dot is aria-hidden; query by class
    const dot = document.querySelector('.pipeline-status-dot')
    expect(dot).toBeInTheDocument()
    expect(dot?.getAttribute('aria-hidden')).toBe('true')
  })
})
