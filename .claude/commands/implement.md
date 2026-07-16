Purpose:
Smart implementation from a plan with automatic parallelization and post-implementation review.

Input:
- `$ARGUMENTS`: Plan reference, task description, or scope. If no plan exists from a prior /analyze, briefly scope the work first.

Steps:

1) Read the plan
- If a plan was produced by /analyze or /feature in this session, use it.
- If arguments describe work directly, create a brief scope: files to change, test strategy, what's excluded.
- If ambiguous, ask for clarification before proceeding.

2) Task decomposition
From the plan, classify each task as:
- **Independent**: Can run in parallel with other tasks
- **Dependent**: Must wait for specific predecessor tasks

3) Parallel implementation
For each group of independent tasks:
- Spawn a builder-sonnet agent per task group
- Each builder: scope lock → TDD (RED → GREEN → REFACTOR) → self-verify
- Monitor for BLOCKER reports — if any builder is blocked, address before continuing

4) Sequential implementation
For dependent tasks, run in dependency order after prerequisites complete.

5) Tiered review gate

Before invoking `critic-opus`:
1. Run `python-reviewer` on the diff first.
2. Escalate to `critic-opus` ONLY if any of:
   - `python-reviewer` reports ISSUES (any severity)
   - Diff touches >5 files
   - Diff touches `app/auth/**`, `app/api/v1/**`, `alembic/**`, or files matching `*security*`, `*permission*`, `*token*`
3. Otherwise emit `REVIEW: SKIPPED-CLEAN (python-reviewer passed, low-risk diff)` and proceed.

6) Auto-review (critic-opus — conditional, see gate above)
After ALL builders finish, automatically spawn critic-opus:
- Review all changed files against the plan/spec
- Run: ruff, mypy, pytest
- If CRITICAL or HIGH issues → spawn builder-sonnet to fix → re-review
- Loop until APPROVE verdict
- If critic-opus emits `FRONTEND-INTEGRATION-REQUIRED`, spawn builder-sonnet to author/update the frontend integration guide (builder delegates the Markdown authoring to writer-haiku; guide lives under `docs/frontend/`) before finalizing. Include the guide path in the report.

6) Report
- Tasks completed
- Files changed
- Tests added and pass status
- Review verdict
- Any follow-up items

## Inter-agent handoffs

After each phase, write artifact to `.claude/scratch/<task-id>/<phase>.md` and pass the *path* to the next agent — NOT the contents. Phases:
- `plan.md` (architect output)
- `diff-summary.md` (builder output)
- `review.md` (critic output)

Use COMPACT mode for these handoff artifacts. The final user-facing summary at the end of `/implement` is terse-professional (brief) per `.claude/rules/core.md` — expand to prose only if the user asks or an explanation is load-bearing.
