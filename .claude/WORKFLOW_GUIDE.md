# .claude Workflow Guide

## Goal
Use the `.claude` folder as an operating system for AI-assisted development:
- Automated planning/build/review pipelines
- Persistent memory between sessions
- Up-to-date architecture + changelog context
- Specialized agents with model-pinned roles

---

## Agents

| Agent | Model | Purpose |
|---|---|---|
| `architect-opus` | Opus | Analysis, architecture, RADAR methodology |
| `builder-sonnet` | Sonnet | Implementation, TDD, clean code |
| `bug-fixer-sonnet` | Sonnet | Surgical bug fixes after diagnosis |
| `critic-opus` | Opus | Security/correctness review (auto after every impl) |
| `debugger-buddy` | Sonnet | Bug diagnosis, root-cause analysis |
| `writer-haiku` | Haiku | Documentation, plans, changelogs |
| `python-reviewer` | Sonnet | Automated lint/type/security tooling |

## Pipeline Commands (Primary Workflow)

| Command | What It Does |
|---|---|
| `/feature <desc>` | Full pipeline: analyze → approve → implement (parallel) → review → simplify → docs |
| `/analyze <problem>` | Deep RADAR analysis → recommendation + plan |
| `/implement <plan>` | Auto-parallel builders → auto-review |
| `/review [files]` | Critic review + automated tooling |
| `/fix <bug>` | Diagnose → fix → review → document |

### Utility Commands

| Command | What It Does |
|---|---|
| `/add <files>` | Load files as mandatory context |
| `/update-summary` | Update architecture docs + CHANGELOG_AI.md |
| `/update-memory` | Update all memory files |
| `/record-decision` | Record architectural decision |
| `/record-bug` | Record bug fix |
| `/record-pattern` | Record reusable pattern |
| `/session-summary` | End-of-session summary |
| `/verify-writing` | Check writer-haiku provenance markers |

---

## Daily Workflow

### Session Start
1. Context auto-loads: `active.yaml`, core rules.
2. If docs lag behind code, run `/update-summary`.
3. Decide your path:
   - New feature → `/feature`
   - Bug → `/fix`
   - Architecture question → `/analyze`
   - Quick change → just describe it (builder + auto-review)

### During Work
- Pipeline commands handle orchestration — no need to manually invoke each agent.
- Architect decides parallelization. Builder agents run in parallel for independent tasks.
- Critic auto-reviews after every implementation.
- Record decisions/bugs/patterns as they happen.

### Session End
- Run `/update-memory` to persist learnings.
- Run `/update-summary` if architecture/contracts changed.

---

## Key Files

### Core Contracts
- `CLAUDE.md` (root): Model routing, pipeline commands, session protocol
- `.claude/AGENTS.md`: Agent architecture, orchestration patterns, escalation rules
- `.claude/constitution.md`: Immutable guardrails (security, testing, deployment)
- `.claude/CLAUDE.md`: Python stack standards

### Agents (`.claude/agents/`)
Each file defines a model-pinned specialist with embedded instructions.

### Prompt Packs (manual reference)
- `.claude/architect.md`, `.claude/builder.md`, `.claude/critic.md`: Detailed prompt templates for manual use outside Claude Code.
- `.claude/frontend-architect.md`, `.claude/frontend-builder.md`: Frontend prompts.

### Templates
- `.claude/TEMPLATES/spec.md`: Feature spec (WHAT + WHY)
- `.claude/TEMPLATES/plan.md`: Implementation plan (HOW)
- `.claude/TEMPLATES/Prompt_Template_RADAR.md`: Full RADAR analysis framework (reference)
- `.claude/TEMPLATES/Prompt_Template_IRASF.md`: Research analysis framework (reference)

### Memory System
- `.claude/memory/active.yaml`: Always-loaded compact memory
- `.claude/memory/context.md`: Expanded session context
- `.claude/memory/decisions.md`: Architectural decisions
- `.claude/memory/bugs.md`: Bug fixes with root causes
- `.claude/memory/patterns.md`: Reusable patterns

---

## End-to-End Playbooks

### New Feature
```
/feature "Add user notifications with SSE streaming"
```
Pipeline auto-handles: analysis → plan → approval gate → parallel implementation → review loop → simplify → docs.

### Bug Fix
```
/fix "Login fails with 401 after token refresh"
```
Pipeline auto-handles: diagnosis → regression test → fix → review → bugs.md.

### Architecture Decision
```
/analyze "Redis vs PostgreSQL for session storage"
```
Architect produces: landscape research, 3 approaches, pairwise comparison, recommendation with pre-mortem.

### Quick Task
Just describe it — builder implements with auto-review:
```
"Add logging to the payment service"
```

### Frontend Work
Use frontend-specific files:
- Planning: `.claude/frontend-architect.md`
- Implementation: `.claude/frontend-builder.md`
- Standards: `.claude/frontend-claude.md`

---

## Quality Rules (Non-Negotiable)
- Respect `.claude/constitution.md`.
- Tests required for behavior changes (TDD).
- Critic review after every implementation.
- No new dependencies without verification.
- Architecture/changelog updated after significant changes.
- Prefer existing libraries over custom code.
- Security first in all implementations.
