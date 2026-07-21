import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DataBar } from './DataBar'

describe('DataBar', () => {
  it('is collapsed by default, hiding the upload drop zone', () => {
    render(<DataBar state={{ phase: 'idle' }} onStateChange={vi.fn()} />)
    expect(screen.queryByText('Click or drop a CSV or JSON file to begin')).toBeNull()
  })

  it('expands to show the upload drop zone on click', () => {
    render(<DataBar state={{ phase: 'idle' }} onStateChange={vi.fn()} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByText('Click or drop a CSV or JSON file to begin')).toBeInTheDocument()
  })

  it('shows a compact summary of the loaded dataset when ready', () => {
    render(
      <DataBar
        state={{
          phase: 'ready',
          sessionId: 's1',
          rowCount: 500,
          tableName: 'uploaded_data',
          joinKeyColumn: null,
          joinKeyTable: null,
          suggestedQuestions: [],
        }}
        onStateChange={vi.fn()}
      />,
    )
    expect(screen.getByText('uploaded_data · 500 rows loaded')).toBeInTheDocument()
  })
})
