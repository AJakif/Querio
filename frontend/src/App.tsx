import { useState, useCallback, useRef, useEffect } from 'react'
import { ChatThread } from './components/ChatThread'
import { askQuestion } from './api/askApi'
import { UploadZone, type UploadState } from './components/UploadZone'
import { teardownSession } from './api/uploadApi'
import type { ChatMessage } from './types/api'

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | undefined>()
  const [uploadState, setUploadState] = useState<UploadState>({ phase: 'idle' })

  const latestSessionIdRef = useRef<string | undefined>(undefined)

  useEffect(() => {
    if (uploadState.phase === 'ready') {
      latestSessionIdRef.current = uploadState.sessionId
    }
  }, [uploadState])

  const sessionId = uploadState.phase === 'ready' ? uploadState.sessionId : undefined

  const handleClearSession = useCallback(async () => {
    const sid = latestSessionIdRef.current
    if (!sid) return
    latestSessionIdRef.current = undefined
    try {
      await teardownSession(sid)
    } catch {
      // best-effort; session will be orphaned but won't block the user
    }
  }, [])

  useEffect(() => {
    function onBeforeUnload() {
      const sid = latestSessionIdRef.current
      if (!sid) return
      navigator.sendBeacon(`/api/session/${encodeURIComponent(sid)}/teardown`)
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [])

  const handleSend = useCallback(async (question: string) => {
    setLoading(true)
    setError(undefined)
    setMessages((prev) => [...prev, { type: 'user', question }])
    try {
      const response = await askQuestion(question, undefined, undefined, sessionId)
      setMessages((prev) => [...prev, response])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  const handleClarify = useCallback(async (conversationId: string, option: string) => {
    setLoading(true)
    setError(undefined)
    setMessages((prev) => [...prev, { type: 'user', question: option }])
    try {
      const response = await askQuestion(option, conversationId, option, sessionId)
      setMessages((prev) => [...prev, response])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Querio</h1>
      </header>
      <main className="app-main">
        <UploadZone
          state={uploadState}
          onStateChange={setUploadState}
          currentSessionId={sessionId}
          onClearSession={handleClearSession}
          onSuggestionSelect={handleSend}
        />
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
