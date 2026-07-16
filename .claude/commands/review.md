Purpose:
Security and correctness review of recent changes using critic-opus plus automated tooling.

Input:
- `$ARGUMENTS`: Optional — specific files or scope. If empty, reviews all uncommitted changes.

Steps:

1) Determine scope
- If arguments provided, review those files/components.
- If no arguments, use `git diff --name-only` for uncommitted changes.
- If nothing uncommitted, use `git diff HEAD~1 --name-only` for last commit.
- If still empty, inform user there's nothing to review.

2) Load context
- Read relevant specs/plans if they exist for the changes being reviewed.
- Read the changed files.

3) Run automated checks (parallel)
Execute in parallel:
- `uv run ruff check .` (lint)
- `uv run mypy .` (type check)
- `uv run pytest --tb=short` (tests)

4) Spawn critic-opus
Pass changed files and any spec/plan context for review:
- Security, correctness, clean code, performance, architecture compliance
- AI bias awareness (reviewing AI-generated code)
- Issue prioritization: CRITICAL → HIGH → MEDIUM → LOW
- Frontend integration impact: critic must emit `FRONTEND-INTEGRATION-REQUIRED` when a created/modified API surface needs frontend work (or `FRONTEND-INTEGRATION: not required`).
- Verdict: APPROVE / REQUEST CHANGES / REJECT

5) Frontend integration follow-through
- If critic-opus emitted `FRONTEND-INTEGRATION-REQUIRED`, route to `builder-sonnet` to create or update the frontend integration guide. `builder-sonnet` delegates the Markdown authoring to `writer-haiku` (guide lives under `docs/frontend/`). Surface the resulting guide path in the results.
- If the critic reported `FRONTEND-INTEGRATION: not required`, note it and move on.

6) Deploy/ops follow-through
- If critic-opus emitted `OPS-ACTION-REQUIRED`, route to `builder-sonnet` to append a structured entry to `infra/docs/deploy-runbook.md` using the entry template. Builder fills every field it can infer from the diff + trigger map; fields needing a human (Owner name, exact Order vs other deploys) are written `TBD — <what's needed>`. Surface the new `RB-id` and the file path in the results.
- If the critic reported `not required`, note it and move on.

7) Present combined results
- Automated check results (lint, types, tests)
- Critic findings with severity and concrete fixes
- Overall verdict
- If REQUEST CHANGES or REJECT, list specific issues to address
