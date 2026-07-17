<!-- written-by: writer-haiku | model: haiku -->

# Contributing to Querio

Thanks for considering a contribution! This guide will help you get started.

## What We Welcome

- **Bug fixes** — correctness issues, data pipeline bugs, UI glitches.
- **Demo questions** — new example queries that showcase the dataset or agentic features. See [`DEMO_QUESTIONS.md`](./docs/DEMO_QUESTIONS.md).
- **Dataset and dbt improvements** — better transformations, clearer mart schemas, richer demo data.
- **Frontend polish** — visual refinements, accessibility improvements, better error messages.
- **Agent capability improvements** — smarter clarifying questions, better guardrail diagnostics, provider adapter fixes.

## What's Out of Scope

This is a **single-user POC by design** (see [`README.md` known limitations](./README.md#known-limitations)). We don't currently accept:

- Multi-tenancy features
- User authentication / authorization (beyond lightweight local accounts for verify/share)
- Write SQL operations (read-only by design)
- LLM provider configuration via UI (config-only for now)

---

## Before You Start

1. **Set up locally** — Follow [`docs/SETUP.md`](./docs/SETUP.md) for Docker Compose setup and environment configuration.
2. **Review the architecture** — [`ARCHITECTURE.md`](./docs/ARCHITECTURE.md) covers the system design; the [root `CLAUDE.md`](./CLAUDE.md) documents layering rules and guardrails.
3. **Skim the guardrail boundary** — the "Security-relevant boundaries" section of [`CLAUDE.md`](./CLAUDE.md) describes the security-critical SQL validator. Any backend change touching SQL execution must preserve this boundary.

---

## Development Flow

### Branch Naming

Follow the pattern observed in this repo:

```
feature/epic-N-short-description
```

Examples: `feature/epic-7-agent-contracts`, `feature/epic-8-conversation-surface`

### Layering Rules (Backend)

The backend follows a strict layering boundary:

```
API routes → schemas (DTOs) → services → repositories → guardrails
```

Keep this boundary enforced:
- **No DB access outside repositories** (`backend/app/repositories/`)
- **All external input validated at service/API boundaries**
- **Generated SQL never bypasses `guardrails/sql_validator.py`** — this is a hard security boundary (SELECT-only, row cap, timeout). Do not add alternative query paths.

### Running Tests

From **backend/**:
```bash
pytest --cov              # all tests with coverage
pytest tests/unit         # unit tests only
pytest tests/integration  # integration (needs live Postgres)
```

From **frontend/**:
```bash
npm run test              # single run (vitest)
npm run test:watch        # watch mode (vitest)
```

### Code Quality

**No automated lint/format tooling is wired up yet** — the primary quality gate is the test suite. When the house rules get tooling, expect:
- **Type hints:** strict mypy, modern syntax (`list[X]`, `dict[K,V]`, `X | None`), no bare `Any`
- **Backend:** repository → service → API layering, no blocking I/O in async functions, explicit error handling
- **Frontend:** colocated tests next to components, React Testing Library against real trees

### What "Done" Looks Like

1. Targeted tests pass (new behavior is tested; refactors maintain existing coverage).
2. Touched files are type-clean and follow the layering rules.
3. If your change affects the API contract, database schema, or system architecture, update the relevant docs (see [`CLAUDE.md`](./CLAUDE.md) section "Before architecture-affecting work").

---

## Testing Expectations

We follow a **load-bearing tests only** philosophy. Every test must satisfy all four of these criteria; if it doesn't, it gets dropped:

1. **Failure signal** — Would this test fail if realistic bug were introduced?
2. **User-visible consequence** — Would a user or operator notice if this behavior broke?
3. **Non-redundant** — Does another test already catch this failure?
4. **Not testing the framework** — Are you testing your code, not Pydantic / FastAPI / React Testing Library?

### Test Budget by Change Type

| Change | Target | Ceiling |
|--------|--------|---------|
| Single-function bug fix | 1 regression test | 1 (**hard**) |
| New endpoint | 1 happy + 1 validation-boundary | ≤5 |
| New service method | 1 happy + 1 failure + 1 per branch | ≤5 |
| New feature (multi-file) | 3–7 total | ≤10 |
| Refactor | 0 new tests | 0 (**hard**) |

See [`.claude/rules/testing.md`](./.claude/rules/testing.md) for the full policy, including the ban list of test anti-patterns (getter/setter echoes, framework behavior theatre, over-mocking, etc.) and the "delete-first drill."

---

## Commit and PR Conventions

### Commit Messages

Use conventional-commit-style prefixes:

```
feat: add new query type
feat(upload): support JSON shallow flattening
fix: guardrail timeout edge case
docs: update ARCHITECTURE.md for dbt lineage
```

Examples from this repo's history: `feat: replace-on-reupload and session teardown`, `docs: update README for Epic 9/10`.

### Pull Requests

- **Base:** always `main`
- **Description:** include a summary of the change and how it was tested
- **No CI gates** — verification today is local (run the test suites yourself). A human reviewer will audit your change.

### Example PR Shape

```
## Summary
Added support for stacked-bar charts in AnswerCard.

## Test plan
- `npm run test` passes in frontend/
- Manual: opened existing stacked answers, verified chart renders correctly
- Manual: asked new stacked question, verified chart generation works end-to-end
```

---

## Code of Conduct

Be respectful and professional. No harassment, discrimination, or bad-faith engagement. Disagreements are welcome; personal attacks are not.

---

## Questions?

Open an issue or a draft PR if you'd like feedback before diving in. The maintainers are happy to help clarify scope or design before you invest effort.
