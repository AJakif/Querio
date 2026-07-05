import { useState, useRef, useEffect } from 'react'
import type { AskResponse } from '../types/api'
import { ChatBubble } from './ChatBubble'

interface ChatThreadProps {
  messages: AskResponse[]
  onSend: (question: string) => void
  onClarify?: (conversationId: string, option: string) => void
  loading?: boolean
  error?: string
}

export function ChatThread({ messages, onSend, onClarify, loading, error }: ChatThreadProps) {
  const [input, setInput] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) return
    onSend(trimmed)
    setInput('')
  }

  const lastClarifierIdx = findLastClarifierIndex(messages)

  return (
    <div className="chat-thread">
      <div className="messages">
        {messages.map((msg, i) => (
          <ChatBubble
            key={i}
            message={msg}
            onOptionSelect={
              msg.type === 'clarifying_question' && onClarify
                ? (option) => onClarify(msg.conversation_id, option)
                : undefined
            }
            disabled={msg.type === 'clarifying_question' && i !== lastClarifierIdx}
          />
        ))}
        {loading && <div className="loading-indicator">Thinking...</div>}
        {error && <div className="error-message">{error}</div>}
        <div ref={endRef} />
      </div>
      <form className="input-area" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}

function findLastClarifierIndex(messages: AskResponse[]): number {
  let last = -1
  for (let i = 0; i < messages.length; i++) {
    if (messages[i]?.type === 'clarifying_question') {
      last = i
    }
  }
  return last
}
