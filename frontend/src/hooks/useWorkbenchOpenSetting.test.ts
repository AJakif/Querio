import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWorkbenchOpenSetting } from './useWorkbenchOpenSetting'

const STORAGE_KEY = 'querio.workbench.open'

beforeEach(() => {
  localStorage.clear()
})

describe('useWorkbenchOpenSetting', () => {
  it('defaults to false (collapsed) when localStorage has no entry', () => {
    const { result } = renderHook(() => useWorkbenchOpenSetting())
    const [open] = result.current
    expect(open).toBe(false)
  })

  it('persists open state to localStorage and restores it on remount', () => {
    const { result, unmount } = renderHook(() => useWorkbenchOpenSetting())

    // Open the workbench
    act(() => {
      const [, setOpen] = result.current
      setOpen(true)
    })

    expect(localStorage.getItem(STORAGE_KEY)).toBe('true')

    unmount()

    // Remount — simulates page reload reading from localStorage
    const { result: result2 } = renderHook(() => useWorkbenchOpenSetting())
    const [open2] = result2.current
    expect(open2).toBe(true)
  })
})
