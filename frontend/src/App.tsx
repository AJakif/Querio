import { useState, useCallback } from 'react'
import { ChatThread } from './components/ChatThread'
import { askQuestion } from './api/askApi'
import type { ChatMessage } from './types/api'

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | undefined>()

  const handleSend = useCallback(async (question: string) => {
    setLoading(true)
    setError(undefined)
    setMessages((prev) => [...prev, { type: 'user', question }])
    try {
      const response = await askQuestion(question)
      setMessages((prev) => [...prev, response])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleClarify = useCallback(async (conversationId: string, option: string) => {
    setLoading(true)
    setError(undefined)
    setMessages((prev) => [...prev, { type: 'user', question: option }])
    try {
      const response = await askQuestion(option, conversationId, option)
      setMessages((prev) => [...prev, response])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Querio</h1>
      </header>
      <main className="app-main">
        <ChatThread
          messages={messages}
          onSend={handleSend}
          onClarify={handleClarify}
          loading={loading}
          error={error}
        />
      </main>
    </div>
  )
}
