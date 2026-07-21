import { useState } from 'react'

const STORAGE_KEY = 'querio.workbench.open'

/**
 * Persists the workbench drawer open/collapsed state in localStorage.
 * Default: collapsed (false).
 */
export function useWorkbenchOpenSetting(): [boolean, (v: boolean) => void] {
  const [open, setOpen] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored === null ? false : stored === 'true'
    } catch {
      return false
    }
  })

  function set(v: boolean): void {
    setOpen(v)
    try {
      localStorage.setItem(STORAGE_KEY, String(v))
    } catch {
      // Ignore storage errors (private browsing quota exhaustion, etc.)
    }
  }

  return [open, set]
}
