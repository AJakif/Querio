import type { ChatMessage, AnswerResponse, ClarifyingQuestionResponse, UserMessage } from '../types/api'
import { ChartWidget } from './charts/ChartWidget'

interface ChatBubbleProps {
  message: ChatMessage
  onOptionSelect?: (option: string) => void
  disabled?: boolean
}

export function ChatBubble({ message, onOptionSelect, disabled }: ChatBubbleProps) {
  if (message.type === 'user') {
    return <UserBubble message={message} />
  }

  if (message.type === 'clarifying_question') {
    return <ClarifierBubble message={message} onOptionSelect={onOptionSelect} disabled={disabled} />
  }
  return <AnswerBubble message={message} />
}

function UserBubble({ message }: { message: UserMessage }) {
  return (
    <div data-testid="user-bubble" className="bubble user-bubble">
      <div className="bubble-content">
        <p>{message.question}</p>
      </div>
    </div>
  )
}

function AnswerBubble({ message }: { message: AnswerResponse }) {
  return (
    <div data-testid="answer-bubble" className="bubble answer-bubble">
      <div className="bubble-content">
        <p>{message.answer}</p>
        {message.chart && (
          <div className="chart-container">
            <ChartWidget chart={message.chart} />
          </div>
        )}
        {message.sql && (
          <details className="sql-details">
            <summary>SQL</summary>
            <pre><code>{message.sql.sql}</code></pre>
            <p className="sql-explanation">{message.sql.explanation}</p>
          </details>
        )}
      </div>
    </div>
  )
}

function ClarifierBubble({
  message,
  onOptionSelect,
  disabled,
}: {
  message: ClarifyingQuestionResponse
  onOptionSelect?: (option: string) => void
  disabled?: boolean
}) {
  return (
    <div data-testid="clarifier-bubble" className="bubble clarifier-bubble">
      <div className="bubble-content">
        <span className="clarifier-label">Clarification</span>
        <p>{message.question}</p>
        <div className="clarifier-options">
          {message.options.map((option) => (
            <button
              key={option}
              type="button"
              className="clarifier-option"
              onClick={() => onOptionSelect?.(option)}
              disabled={disabled}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
