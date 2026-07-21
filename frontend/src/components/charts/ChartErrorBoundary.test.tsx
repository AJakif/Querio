import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChartErrorBoundary } from './ChartErrorBoundary'

function ThrowingChild(): never {
  throw new Error('recharts exploded')
}

describe('ChartErrorBoundary', () => {
  it('renders fallback when child throws at render time', () => {
    // Suppress the expected React error boundary console.error in test output
    const spy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    render(
      <ChartErrorBoundary fallback={<div data-testid="chart-fallback">fallback shown</div>}>
        <ThrowingChild />
      </ChartErrorBoundary>,
    )
    expect(screen.getByTestId('chart-fallback')).toBeInTheDocument()
    spy.mockRestore()
  })
})
