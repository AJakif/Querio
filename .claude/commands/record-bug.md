Purpose:
Record a bug and its fix in shared project memory.

Target Files:
- `.claude/memory/active.yaml` (update `bugs_open` or clear when resolved)
- `.claude/memory/bugs.md`

Inputs:
- Bug title/description from command arguments: `$ARGUMENTS`
- If no arguments are provided, ask for a short bug title.

Steps:

1) Collect bug scope
- Check staged diff first: `git diff --staged --name-only`
- If empty, use last commit: `git show --name-only --pretty=""`
- Identify files and tests relevant to the bug fix.

2) Append a bug entry to `bugs.md`
- Use heading format: `## [Bug Title]`
- Include:
  - **Symptom**
  - **Root Cause**
  - **Fix**
  - **Prevention**
  - **Files** (affected paths)

3) Update `active.yaml`
- If the bug is still active, add/update under `bugs_open`.
- If fixed, ensure it is not listed as open.
- Keep only current, high-priority bug pointers.

4) Quality checks
- Keep it concise and reproducible.
- Include what prevents recurrence (test, validation, guardrail).
- Avoid vague statements like "fixed issue" without root cause.
- Keep `active.yaml` compact (pointer-level detail only).

Output:
- Confirm bug update was applied to `active.yaml` and `bugs.md`.
- Show bug title/status and files captured.
