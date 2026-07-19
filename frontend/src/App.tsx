import { useState, useCallback, useRef, useEffect } from 'react'
import { ChatThread } from './components/ChatThread'
import { ChatSessionHistoryMenu } from './components/ChatSessionHistoryMenu'
import { useThinkingStream } from './hooks/useThinkingStream'
import { EmptyStateEda } from './components/EmptyStateEda'
import { UploadZone, type UploadState } from './components/UploadZone'
import { teardownSession } from './api/uploadApi'
import { confirmAssumptions } from './api/askApi'
import { createChatSession, getChatSession } from './api/chatSessionApi'
import type { ChatMessage } from './types/api'

const CHAT_SESSION_KEY = 'querio_chat_session_id'

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | undefined>()
  const [uploadState, setUploadState] = useState<UploadState>({ phase: 'idle' })
  const [chatSessionId, setChatSessionId] = useState<string | undefined>()
  const { trace, run: runAsk } = useThinkingStream()

  const latestSessionIdRef = useRef<string | undefined>(undefined)

  // Upload session (sandbox) tracking
  useEffect(() => {
    if (uploadState.phase === 'ready') {
      latestSessionIdRef.current = uploadState.sessionId
    }
  }, [uploadState])

  const sessionId = uploadState.phase === 'ready' ? uploadState.sessionId : undefined

  // ---------------------------------------------------------------------------
  // Chat session lifecycle — on mount, restore or create
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false

    async function initChatSession() {
      const stored = localStorage.getItem(CHAT_SESSION_KEY)

      if (stored) {
        try {
          const history = await getChatSession(stored)
          if (cancelled) return
          // Rehydrate messages from stored turns — pure GET, no /ask call
          const rehydrated: ChatMessage[] = []
          for (const turn of history.turns) {
            rehydrated.push({ type: 'user', question: turn.question })
            rehydrated.push(turn.answer)
          }
          setMessages(rehydrated)
          setChatSessionId(stored)
          return
        } catch {
          if (cancelled) return
          // 404 (stale id) or any other error: fall through to create a fresh session
        }
      }

      // No stored id or stale id — mint a fresh session
      try {
        const session = await createChatSession()
        if (cancelled) return
        localStorage.setItem(CHAT_SESSION_KEY, session.chat_session_id)
        setChatSessionId(session.chat_session_id)
      } catch {
        // Non-fatal: chat still works, turns just won't be persisted
      }
    }

    void initChatSession()
    return () => { cancelled = true }
  }, [])

  // ---------------------------------------------------------------------------
  // Upload session teardown
  // ---------------------------------------------------------------------------
  const handleClearSession = useCallback(async () => {
    const sid = latestSessionIdRef.current
    if (!sid) return
    latestSessionIdRef.current = undefined
    try {
      await teardownSession(sid)
    } catch {
      // best-effort
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

  // ---------------------------------------------------------------------------
  // History menu: switch to a past session
  // ---------------------------------------------------------------------------
  const handleSelectSession = useCallback(async (id: string) => {
    try {
      const history = await getChatSession(id)
      const rehydrated: ChatMessage[] = []
      for (const turn of history.turns) {
        rehydrated.push({ type: 'user', question: turn.question })
        rehydrated.push(turn.answer)
      }
      setMessages(rehydrated)
      setChatSessionId(id)
      localStorage.setItem(CHAT_SESSION_KEY, id)
    } catch {
      // If session vanished between listing and fetching, ignore
    }
  }, [])

  // ---------------------------------------------------------------------------
  // Ask handlers
  // ---------------------------------------------------------------------------
  const handleSend = useCallback(async (question: string) => {
    setLoading(true)
    setError(undefined)
    setMessages((prev) => [...prev, { type: 'user', question }])
    try {
      const response = await runAsk(question, undefined, undefined, sessionId, chatSessionId)
      setMessages((prev) => [...prev, response])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }, [sessionId, chatSessionId, runAsk])

  const handleClarify = useCallback(async (conversationId: string, option: string) => {
    setLoading(true)
    setError(undefined)
    setMessages((prev) => [...prev, { type: 'user', question: option }])
    try {
      const response = await runAsk(option, conversationId, option, sessionId, chatSessionId)
      setMessages((prev) => [...prev, response])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }, [sessionId, chatSessionId, runAsk])

  // Note: /ask/confirm does NOT accept chat_session_id (backend teammate did not extend it).
  // Confirmed-assumption answers are therefore not persisted. Flagged as a gap.
  const handleConfirm = useCallback(
    async (conversationId: string, amendments: { term: string; resolution: string }[]) => {
      setLoading(true)
      setError(undefined)
      try {
        const response = await confirmAssumptions(conversationId, amendments)
        setMessages((prev) => [...prev, response])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred')
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  return (
    <div className="app">
      <header className="app-header">
        <h1>Querio</h1>
        <ChatSessionHistoryMenu onSelectSession={handleSelectSession} />
      </header>
      <main className="app-main">
        <UploadZone
          state={uploadState}
          onStateChange={setUploadState}
          currentSessionId={sessionId}
          onClearSession={handleClearSession}
          onSuggestionSelect={handleSend}
        />
        {messages.length === 0 && <EmptyStateEda sessionId={sessionId} onSend={handleSend} />}
        <ChatThread
          messages={messages}
          onSend={handleSend}
          onClarify={handleClarify}
          onConfirm={handleConfirm}
          loading={loading}
          error={error}
          trace={trace}
        />
      </main>
    </div>
  )
}
