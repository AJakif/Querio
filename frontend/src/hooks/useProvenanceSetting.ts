import { useState } from 'react'

const STORAGE_KEY = 'querio.export.provenance'

/**
 * Persists the "include provenance footer in exports" toggle in localStorage.
 * Default: enabled (true).
 */
export function useProvenanceSetting(): [boolean, (v: boolean) => void] {
  const [enabled, setEnabled] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored === null ? true : stored === 'true'
    } catch {
      return true
    }
  })

  function set(v: boolean): void {
    setEnabled(v)
    try {
      localStorage.setItem(STORAGE_KEY, String(v))
    } catch {
      // Ignore storage errors (private browsing quota exhaustion, etc.)
    }
  }

  return [enabled, set]
}
