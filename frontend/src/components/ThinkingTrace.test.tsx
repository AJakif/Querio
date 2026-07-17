import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ThinkingTrace } from './ThinkingTrace'

describe('ThinkingTrace', () => {
  it('renders completed agents as checked and pending agents as spinning', () => {
    render(
      <ThinkingTrace
        steps={[
          { type: 'step', stage: 'planner', detail: { ambiguity_score: 0.3, unresolved_terms: ['orders'] } },
        ]}
      />,
    )

    const planner = screen.getByText('Planner').closest('.thinking-trace-row')
    const sqlGenerator = screen.getByText('SQL Generator').closest('.thinking-trace-row')

    expect(planner).toHaveClass('done')
    expect(sqlGenerator).toHaveClass('pending')
    expect(screen.getByText(/Ambiguity 30%/)).toBeInTheDocument()
  })
})
