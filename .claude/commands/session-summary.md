Purpose:
Generate and apply an end-of-session summary to shared project memory.

Target Files:
- `.claude/memory/active.yaml` (required)
- `.claude/memory/context.md`

Inputs:
- Optional scope from command arguments: `$ARGUMENTS`
- Prefer staged changes.
- If nothing is staged, use last commit.

Steps:

1) Detect session scope
- Use: `git diff --staged --name-only`
- If empty, use: `git show --name-only --pretty=""`
- If arguments are provided, prioritize that scope.

2) Summarize work completed
- Capture key completed items from this session.
- Capture in-progress items and blockers.
- Capture immediate next steps.

3) Update `active.yaml`
- Refresh:
  - `updated`
  - `current_focus`
  - `recent_changes`
  - `open_blockers`
  - `next_steps`
- Keep the file compact and actionable.

4) Update `context.md` (archive-level detail)
- Refresh:
  - `Current Focus`
  - `Recent Changes`
  - `Blocked/Pending`
- Move completed or stale items out of active focus.

5) Quality checks
- Keep summary concise and factual.
- Include affected files where useful.
- Avoid repeating detailed changelog text.
- Keep `active.yaml` small (target <= 60 lines).

Output:
- Print session summary (completed, in-progress, blockers, next steps).
- Confirm `active.yaml` and `context.md` were updated.
