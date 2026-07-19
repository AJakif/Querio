import { useState, useEffect, useRef, useCallback } from 'react'
import { listChatSessions } from '../api/chatSessionApi'
import type { ChatSessionSummaryResponse } from '../types/api'

interface ChatSessionHistoryMenuProps {
  onSelectSession: (chatSessionId: string) => void
}

function formatRelativeDate(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function ChatSessionHistoryMenu({ onSelectSession }: ChatSessionHistoryMenuProps) {
  const [open, setOpen] = useState(false)
  const [sessions, setSessions] = useState<ChatSessionSummaryResponse[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  const loadSessions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await listChatSessions()
      // Sort newest first by updated_at
      const sorted = [...list].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      )
      setSessions(sorted)
    } catch {
      setError('Could not load session history.')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleToggle = () => {
    if (!open) loadSessions()
    setOpen((prev) => !prev)
  }

  const handleSelect = (id: string) => {
    setOpen(false)
    onSelectSession(id)
  }

  // Close menu on outside click
  useEffect(() => {
    if (!open) return
    function onPointerDown(e: PointerEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [open])

  return (
    <div className="chat-history-menu" ref={menuRef}>
      <button
        className="chat-history-btn"
        onClick={handleToggle}
        aria-haspopup="listbox"
        aria-expanded={open}
        title="Session history"
      >
        History
      </button>

      {open && (
        <div className="chat-history-dropdown" role="listbox" aria-label="Past sessions">
          {loading && <div className="chat-history-state">Loading…</div>}
          {error && <div className="chat-history-state chat-history-error">{error}</div>}
          {!loading && !error && sessions.length === 0 && (
            <div className="chat-history-state">No past sessions.</div>
          )}
          {!loading &&
            sessions.map((s) => (
              <button
                key={s.chat_session_id}
                className="chat-history-item"
                role="option"
                onClick={() => handleSelect(s.chat_session_id)}
              >
                <span className="chat-history-preview">
                  {s.preview_question ?? 'Untitled session'}
                </span>
                <span className="chat-history-meta">
                  {s.turn_count} turn{s.turn_count !== 1 ? 's' : ''} &middot;{' '}
                  {formatRelativeDate(s.updated_at)}
                </span>
              </button>
            ))}
        </div>
      )}
    </div>
  )
}
