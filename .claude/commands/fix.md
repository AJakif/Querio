Purpose:
Bug fix pipeline: diagnose → fix → review → document.

Input:
- `$ARGUMENTS`: Bug description, error message, stack trace, or reproduction steps

Steps:

1) DIAGNOSE (debugger-buddy)
Spawn debugger-buddy with the bug description:
- Collect symptoms, read actual tracebacks
- Form 3 ranked hypotheses
- Systematically investigate (highest likelihood first)
- Produce root cause diagnosis with fix approach

Present diagnosis to confirm before proceeding.

2) FIX (bug-fixer-sonnet)
Spawn bug-fixer-sonnet with the diagnosis:
- Verify root cause in the code
- Write regression test (must fail before fix)
- Apply minimal fix (smallest change that resolves root cause)
- Verify regression test passes + no side effects

3) TIERED REVIEW GATE

Before invoking `critic-opus`:
1. Run `python-reviewer` on the diff first.
2. Escalate to `critic-opus` ONLY if any of:
   - `python-reviewer` reports ISSUES (any severity)
   - Diff touches >5 files
   - Diff touches `app/auth/**`, `app/api/v1/**`, `alembic/**`, or files matching `*security*`, `*permission*`, `*token*`
3. Otherwise emit `REVIEW: SKIPPED-CLEAN (python-reviewer passed, low-risk diff)` and proceed.

4) REVIEW (critic-opus — conditional, see gate above)
Spawn critic-opus to review the fix:
- Security impact check
- Side effect analysis
- Verify no new issues introduced
- If issues found → fix → re-review

5) DOCUMENT
- Record bug in `.claude/memory/bugs.md` using /record-bug format:
  - Symptom, root cause, fix, files, prevention
- Update `.claude/CHANGELOG_AI.md` if the fix is significant

6) SUMMARY
Report:
- Root cause identified
- Fix applied (files changed)
- Regression test added
- Review verdict
- Prevention measures

## Inter-agent handoffs

After each phase, write artifact to `.claude/scratch/<task-id>/<phase>.md` and pass the *path* to the next agent — NOT the contents. Phases:
- `plan.md` (architect output)
- `diff-summary.md` (builder output)
- `review.md` (critic output)

Use COMPACT mode for these handoff artifacts. The final user-facing summary at the end of `/fix` is terse-professional (brief) per `.claude/rules/core.md` — expand to prose only if the user asks or an explanation is load-bearing.
