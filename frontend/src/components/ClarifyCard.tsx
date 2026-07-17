import type { ClarifyResponse, ProxyAlternative } from '../types/api'

interface ClarifyCardProps {
  message: ClarifyResponse
  onSend?: (question: string) => void
  onAddData?: () => void
  disabled?: boolean
}

export function ClarifyCard({ message, onSend, onAddData, disabled }: ClarifyCardProps) {
  return (
    <div data-testid="clarify-card" className="bubble clarify-bubble">
      <div className="bubble-content">
        <span className="clarify-label">Data not available</span>
        <p data-testid="clarify-statement" className="clarify-statement">
          {message.statement}
        </p>
        <div data-testid="clarify-alternatives" className="clarify-alternatives">
          {message.alternatives.map((alt: ProxyAlternative) => (
            <button
              key={alt.question}
              type="button"
              className="clarify-proxy-btn"
              onClick={() => onSend?.(alt.question)}
              disabled={disabled}
              data-testid="proxy-btn"
            >
              {alt.label}
            </button>
          ))}
        </div>
        {message.add_data && (
          <button
            type="button"
            className="clarify-add-data-btn"
            onClick={onAddData}
            data-testid="add-data-btn"
          >
            Upload your own data
          </button>
        )}
      </div>
    </div>
  )
}
