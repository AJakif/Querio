# Frontend Stack Configuration

<!--
USAGE: Import into project's CLAUDE.md with:
> Stack-specific rules imported from .claude/frontend-claude.md
-->

## Token discipline (mandatory)
- Do not ask me to paste long logs, lockfiles, or generated output into chat.
- If output is large, tell me to save it to a file and reference it with `@path`.
- If I paste >150 lines or >10k characters, stop and ask me to move it into a file.
- Prefer commands that redirect output to files and then read the file.

## Always-load project context
Before planning or coding, read:
- `@architecture/system-model.yaml`
- `@CHANGELOG_AI.md`

If missing or stale relative to recent code changes, run `/update-summary` before proceeding.
When changes affect architecture, routes, shared UI patterns, or state/data flow, update architecture docs in the same PR.

## Runtime & Tooling

| Component | Choice |
|-----------|--------|
| Runtime | Node.js 20+ |
| Package Manager | pnpm (preferred) / npm |
| Build Tool | Vite |
| Language | TypeScript (strict) |
| UI | React |
| Component System | shadcn-ui |
| Styling | Tailwind CSS |
| Lint | ESLint |
| Format | Prettier |
| Tests | Vitest + React Testing Library |
| E2E (optional) | Playwright |

---

## Project Structure

```text
project/
├── src/
│   ├── app/                 # app bootstrap, providers, routes
│   ├── components/
│   │   ├── ui/              # shadcn primitives
│   │   └── shared/          # reusable domain-agnostic components
│   ├── features/            # feature-first modules
│   │   └── [feature]/
│   │       ├── api/
│   │       ├── components/
│   │       ├── hooks/
│   │       ├── types.ts
│   │       └── index.ts
│   ├── hooks/
│   ├── lib/                 # utilities (cn, formatters, constants)
│   ├── routes/
│   ├── styles/
│   └── main.tsx
├── public/
├── tests/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

---

## TypeScript Rules

### Required Settings
- `"strict": true`
- `"noImplicitAny": true`
- `"exactOptionalPropertyTypes": true`
- `"noUncheckedIndexedAccess": true`

### Preferred Patterns
```ts
// Explicit props
type ButtonProps = {
  onClick: () => void
  children: React.ReactNode
  disabled?: boolean
}

// Discriminated unions for UI state
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; message: string }

// Runtime-safe parsing boundary
type User = { id: string; name: string }
```

### Forbidden
- `any` without explicit justification.
- Non-null assertions (`!`) unless unavoidable and documented.
- Deep prop drilling when composition or local state can solve it.

---

## React Architecture

### Component Guidelines
- Prefer small focused components with clear single responsibility.
- Keep state as local as possible; lift state only when needed.
- Prefer composition over inheritance and over-generalized wrappers.
- Use memoization only when profiling indicates benefit.

### Hooks and Effects
- Keep `useEffect` for external synchronization, not data derivation.
- Derive values in render when cheap and deterministic.
- Encapsulate reusable behavior in custom hooks.
- Ensure effect cleanup for subscriptions, timers, and listeners.

### Data and Async UI
- Every async view must define: loading, empty, success, and error UI.
- Prevent race conditions and stale updates in async workflows.
- Keep API contracts typed at boundaries.

---

## shadcn-ui + Tailwind Rules

### UI System
- Reuse existing `src/components/ui/*` primitives before creating new components.
- Follow existing variant conventions (`variant`, `size`) consistently.
- Keep shared UI tokens centralized in Tailwind/theme config.

### Tailwind
- Keep class lists readable and grouped by intent (layout, spacing, typography, state).
- Use `cn(...)` helper for conditional classes.
- Avoid inline styles unless dynamic values cannot be represented with utility classes.

---

## Accessibility Standards

- Use semantic HTML before ARIA.
- All interactive elements must be keyboard accessible.
- Inputs require associated labels and clear error messages.
- Visible focus styles must remain intact.
- Respect `prefers-reduced-motion` for non-essential animations.
- Ensure color contrast meets WCAG AA.

---

## Testing Standards

### Required Coverage Areas
- Critical user flows (happy path).
- Validation and error handling.
- Loading and empty states.
- Key accessibility interactions (keyboard/focus/labels).

### Testing Style
```ts
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

describe("ProfileCard", () => {
  it("shows loading state while data is pending", () => {
    // Arrange / Act / Assert
  })
})
```

---

## Performance Guidelines

- Route-level code splitting for heavy pages.
- Defer non-critical UI and assets.
- Avoid unnecessary parent re-renders from unstable props/functions.
- Optimize image sizes and formats.
- Measure before and after using Lighthouse or Web Vitals.

---

## Security and Reliability

- Do not trust client input; validate at both UI boundary and server boundary.
- Never expose secrets in client bundles.
- Handle network failures and retries intentionally.
- Keep error messages useful but avoid leaking sensitive internals.

---

## Common Commands

```bash
# Install
pnpm install

# Dev server
pnpm dev

# Type checking
pnpm tsc --noEmit

# Testing
pnpm test
pnpm test --coverage

# Lint and format
pnpm lint
pnpm format

# Build and preview
pnpm build
pnpm preview
```

---

## Pre-PR Checklist

- `tsc --noEmit` passes
- tests pass for changed behavior
- lint and formatting pass
- loading/empty/error states handled
- keyboard and focus behavior verified
- mobile and desktop layouts checked
- no unrelated refactors included
