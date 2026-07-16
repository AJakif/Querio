Purpose:
Orchestrate a complete feature implementation: analyze → approve → implement (parallel) → review → document.

Input:
- `$ARGUMENTS`: Feature description or requirement

Pipeline:

1) ANALYZE (architect-opus)
Spawn architect-opus with the feature requirement and project context:
- Load `architecture/system-model.yaml` and `.claude/CHANGELOG_AI.md` as context
- Architect analyzes with epistemic rigor: problem understanding, landscape research (library-first), 3 approaches, pairwise comparison
- Produces: recommendation, spec, plan, parallelized task list

Present the architect's plan to the user for review.

2) APPROVE
Wait for user approval. If changes requested, re-engage architect-opus with feedback.
Do NOT proceed to implementation without explicit user approval of the plan.

3) IMPLEMENT (builder-sonnet — auto-parallel)
Based on the architect's task groups:
- Identify independent task groups from the plan
- Spawn parallel builder-sonnet agents for each independent group
- Each builder follows: scope lock → TDD (RED → GREEN → REFACTOR) → self-verify
- Sequence dependent tasks after prerequisites complete

4) TIERED REVIEW GATE

Before invoking `critic-opus`:
1. Run `python-reviewer` on the diff first.
2. Escalate to `critic-opus` ONLY if any of:
   - `python-reviewer` reports ISSUES (any severity)
   - Diff touches >5 files
   - Diff touches `app/auth/**`, `app/api/v1/**`, `alembic/**`, or files matching `*security*`, `*permission*`, `*token*`
3. Otherwise emit `REVIEW: SKIPPED-CLEAN (python-reviewer passed, low-risk diff)` and proceed.

5) REVIEW (critic-opus — conditional, see gate above)
After all implementation completes, automatically spawn critic-opus to review ALL changes:
- Security, correctness, clean code, performance, architecture compliance
- Run diagnostic commands: ruff, mypy, pytest
- If CRITICAL or HIGH issues found → spawn builder-sonnet to fix → re-review
- Repeat until APPROVE verdict

6) SIMPLIFY
After review passes, run /simplify on the changed code to check for unnecessary complexity.
If simplifications found, apply them and re-run critic review.

7) DOCUMENT (writer-haiku — automatic)
Spawn writer-haiku to:
- Update `.claude/CHANGELOG_AI.md` with changes
- Update architecture docs if contracts, schema, or flows changed
- Create/update any documentation artifacts

8) SUMMARY
Report to user:
- Files created/modified
- Tests added and status
- Review verdict
- Documentation updated
- Any remaining items or follow-ups

## Inter-agent handoffs

After each phase, write artifact to `.claude/scratch/<task-id>/<phase>.md` and pass the *path* to the next agent — NOT the contents. Phases:
- `plan.md` (architect output)
- `diff-summary.md` (builder output)
- `review.md` (critic output)

Use COMPACT mode for these handoff artifacts. The final user-facing summary at the end of `/feature` is terse-professional (brief) per `.claude/rules/core.md` — expand to prose only if the user asks or an explanation is load-bearing.
