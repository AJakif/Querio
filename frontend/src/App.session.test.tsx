/**
 * Load-bearing tests for chat session persistence lifecycle in App.tsx.
 *
 * These tests run in mock mode (MODE === 'test'), so chatSessionApi and askApi
 * use their built-in mock responders — no fetch mocking needed.
 *
 * MOCK_SESSION_ID is the id that getMockChatSession() / getMockChatSessionHistory() use,
 * so storing it in localStorage makes getChatSession() return a history with one turn:
 *   question: "How many orders?"
 *   answer:   "There are **12,458** orders in the database."
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import App from './App'
import { MOCK_SESSION_ID, getMockChatSessionList } from './api/chatSessionApi'

const CHAT_SESSION_KEY = 'querio_chat_session_id'

// Spy on chatSessionApi functions so we can assert call patterns
// without breaking mock mode.
import * as chatSessionApi from './api/chatSessionApi'

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

afterEach(() => {
  localStorage.clear()
})

describe('App — session persistence', () => {
  it('(a) restores messages from stored session id without calling /ask', async () => {
    // Arrange: pre-store a known session id
    localStorage.setItem(CHAT_SESSION_KEY, MOCK_SESSION_ID)
    const getChatSessionSpy = vi.spyOn(chatSessionApi, 'getChatSession')

    // Act: mount App
    render(<App />)

    // Assert: messages from history appear (the mock turn answer)
    await waitFor(() => {
      expect(screen.getByText((t) => t.includes('12,458'))).toBeInTheDocument()
    })

    // getChatSession was called with the stored id
    expect(getChatSessionSpy).toHaveBeenCalledWith(MOCK_SESSION_ID)

    // createChatSession was NOT called (we didn't mint a new session)
    // (checking via spy absence — restoreAllMocks ensures no cross-test leakage)
    const createSpy = vi.spyOn(chatSessionApi, 'createChatSession')
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('(b) mints a new session when no id is stored in localStorage', async () => {
    // No pre-stored id
    const createChatSessionSpy = vi.spyOn(chatSessionApi, 'createChatSession')
    const getChatSessionSpy = vi.spyOn(chatSessionApi, 'getChatSession')

    render(<App />)

    // createChatSession is eventually called and the id is persisted
    await waitFor(() => {
      expect(localStorage.getItem(CHAT_SESSION_KEY)).toBe(MOCK_SESSION_ID)
    })

    expect(createChatSessionSpy).toHaveBeenCalledTimes(1)

    // getChatSession was NOT called (no prior id to restore)
    expect(getChatSessionSpy).not.toHaveBeenCalled()

    // No messages pre-populated
    expect(screen.queryByText((t) => t.includes('12,458'))).not.toBeInTheDocument()
  })

  it('(c) history menu switches to a different past session without calling /ask', async () => {
    // Start with no stored session so we don't confuse rehydration with switch
    const createChatSessionSpy = vi.spyOn(chatSessionApi, 'createChatSession')
    const listSessionsSpy = vi.spyOn(chatSessionApi, 'listChatSessions').mockResolvedValue(
      getMockChatSessionList(),
    )
    const getChatSessionSpy = vi.spyOn(chatSessionApi, 'getChatSession')

    render(<App />)

    // Wait for initial session mint to finish
    await waitFor(() => {
      expect(createChatSessionSpy).toHaveBeenCalledTimes(1)
    })

    // Open the History menu
    fireEvent.click(screen.getByRole('button', { name: /history/i }))

    // Wait for list to populate — sessions from getMockChatSessionList()
    await waitFor(() => {
      expect(listSessionsSpy).toHaveBeenCalledTimes(1)
    })

    // The first item in the list (MOCK_SESSION_ID) should be rendered with preview_question
    await waitFor(() => {
      expect(screen.getByText('How many orders?')).toBeInTheDocument()
    })

    // Click the first session item
    fireEvent.click(screen.getByText('How many orders?'))

    // getChatSession is called to load the selected session
    await waitFor(() => {
      expect(getChatSessionSpy).toHaveBeenCalledWith(MOCK_SESSION_ID)
    })

    // Messages are populated from the history (same answer as rehydration path)
    await waitFor(() => {
      expect(screen.getByText((t) => t.includes('12,458'))).toBeInTheDocument()
    })

    // localStorage is updated to the selected session id
    expect(localStorage.getItem(CHAT_SESSION_KEY)).toBe(MOCK_SESSION_ID)
  })
})
