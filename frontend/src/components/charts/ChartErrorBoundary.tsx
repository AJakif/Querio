import { Component } from 'react'
import type { ReactNode, ErrorInfo } from 'react'

interface Props {
  fallback: ReactNode
  children: ReactNode
}

interface State {
  hasError: boolean
}

/**
 * Error boundary wrapping ChartWidget.
 * Catches render-time throws (e.g. from Recharts on malformed data) and
 * swaps in the provided fallback instead of leaving blank space.
 */
export class ChartErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(_error: unknown): State {
    return { hasError: true }
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // Intentionally silent — the fallback UI carries the user-visible message.
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.props.fallback
    }
    return this.props.children
  }
}
