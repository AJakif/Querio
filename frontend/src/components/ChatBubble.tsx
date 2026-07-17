import { useState } from 'react'
import type { ChatMessage, AnswerResponse, ClarifyingQuestionResponse, ClarifyResponse, ConfirmFirstResponse, AssumptionResponse, UserMessage } from '../types/api'
import { ChartWidget } from './charts/ChartWidget'
import { AnswerCard } from './AnswerCard'
import { ClarifyCard } from './ClarifyCard'

interface ChatBubbleProps {
  message: ChatMessage
  onOptionSelect?: (option: string) => void
  onConfirm?: (conversationId: string, amendments: { term: string; resolution: string }[]) => void
  disabled?: boolean
  onSend?: (question: string) => void
}

export function ChatBubble({ message, onOptionSelect, onConfirm, disabled, onSend }: ChatBubbleProps) {
  if (message.type === 'user') {
    return <UserBubble message={message} />
  }

  if (message.type === 'clarifying_question') {
    return <ClarifierBubble message={message} onOptionSelect={onOptionSelect} disabled={disabled} />
  }

  if (message.type === 'clarify') {
    return <ClarifyCard message={message as ClarifyResponse} onSend={onSend} disabled={disabled} />
  }

  if (message.type === 'confirm_first') {
    return <ConfirmGateBubble message={message} onConfirm={onConfirm} disabled={disabled} />
  }

  return <AnswerBubble message={message} onSend={onSend} />
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

function AnswerBubble({ message, onSend }: { message: AnswerResponse; onSend?: (q: string) => void }) {
  // When a structured AnswerSpec is present, route to the appropriate card view.
  // Currently only the stat-only route (ROUTE-1) is handled; extend the switch below
  // when chart-answer and list routes land in later slices.
  if (message.answer_spec) {
    return (
      <div data-testid="answer-bubble" className="bubble answer-bubble">
        <div className="bubble-content">
          <AnswerCard
            spec={message.answer_spec}
            badge={message.badge_state ?? 'unverified'}
            onSend={onSend}
            sql={message.sql}
            validation={message.validation}
            traceSteps={message._trace_steps}
            resultRows={message.result_rows}
          />
        </div>
      </div>
    )
  }

  // Legacy path: plain text answer (no structured spec)
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

function ConfirmGateBubble({
  message,
  onConfirm,
  disabled,
}: {
  message: ConfirmFirstResponse
  onConfirm?: (conversationId: string, amendments: { term: string; resolution: string }[]) => void
  disabled?: boolean
}) {
  const [editValues, setEditValues] = useState<Record<string, string>>(
    Object.fromEntries(message.plan.assumptions.map((a) => [a.term, a.resolution])),
  )

  function handleChipChange(term: string, value: string) {
    setEditValues((prev) => ({ ...prev, [term]: value }))
  }

  function handleConfirm() {
    const amendments = message.plan.assumptions
      .filter((a) => editValues[a.term] !== a.resolution)
      .map((a) => ({ term: a.term, resolution: editValues[a.term] ?? a.resolution }))
    onConfirm?.(message.conversation_id, amendments)
  }

  const gateLabel =
    message.gate_reason === 'cost'
      ? `This query may scan ${message.scan_cost.toLocaleString()} rows`
      : 'Before I run this, please confirm my assumptions'

  return (
    <div data-testid="confirm-gate-bubble" className="bubble confirm-gate-bubble">
      <div className="bubble-content">
        <span className="confirm-gate-label">Confirm before running</span>
        <p className="confirm-gate-reason">{gateLabel}</p>
        <div className="assumption-chips" data-testid="assumption-chips">
          {message.plan.assumptions.map((assumption: AssumptionResponse) => (
            <AssumptionChip
              key={assumption.term}
              assumption={assumption}
              value={editValues[assumption.term] ?? assumption.resolution}
              onChange={(v) => handleChipChange(assumption.term, v)}
              disabled={disabled}
            />
          ))}
        </div>
        <button
          type="button"
          className="confirm-button"
          data-testid="confirm-button"
          onClick={handleConfirm}
          disabled={disabled}
        >
          Confirm &amp; run
        </button>
      </div>
    </div>
  )
}

function AssumptionChip({
  assumption,
  value,
  onChange,
  disabled,
}: {
  assumption: AssumptionResponse
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}) {
  const [editing, setEditing] = useState(false)

  if (editing) {
    return (
      <span className="assumption-chip assumption-chip--editing" data-testid={`chip-${assumption.term}`}>
        <span className="chip-term">{assumption.term}:</span>
        <input
          className="chip-input"
          autoFocus
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={() => setEditing(false)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === 'Escape') setEditing(false)
          }}
          disabled={disabled}
          aria-label={`Edit assumption: ${assumption.term}`}
        />
      </span>
    )
  }

  return (
    <button
      type="button"
      className="assumption-chip"
      data-testid={`chip-${assumption.term}`}
      onClick={() => !disabled && setEditing(true)}
      disabled={disabled}
      title="Click to edit"
    >
      <span className="chip-term">{assumption.term}:</span>
      <span className="chip-resolution">{value}</span>
      <span className="chip-edit-hint" aria-hidden="true">&#9998;</span>
    </button>
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
