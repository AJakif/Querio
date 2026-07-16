Purpose:
Update shared project memory using a lean hybrid model:
- compact active memory (`active.yaml`) for always-loaded context
- detailed markdown archives for durable history

Memory Files:
- `.claude/memory/active.yaml` (always-loaded, keep concise)
- `.claude/memory/context.md`
- `.claude/memory/decisions.md`
- `.claude/memory/bugs.md`
- `.claude/memory/patterns.md`

Inputs:
- Optional scope from command arguments: `$ARGUMENTS`
- Prefer staged changes.
- If nothing is staged, use the last commit.
- If both are unavailable, ask for a scope and use git diff against main.

Steps:

1) Detect scope of change
- Use: `git diff --staged --name-only`
- If empty, use: `git show --name-only --pretty=""`
- If command args are provided, prioritize those files/domains.

2) Update `active.yaml` first (required)
- Refresh:
  - `updated`
  - `current_focus`
  - `recent_changes`
  - `open_blockers`
  - `decisions_recent`
  - `bugs_open`
  - `patterns_active`
  - `next_steps`
- Keep `active.yaml` compact and high-signal.
- Prefer pointers/references to detailed archive entries.

3) Update `context.md` when expanded session detail is useful
- Keep entries concise and factual.
- Update `Current Focus`, `Recent Changes`, and `Blocked/Pending`.
- Move stale or completed items out of `Current Focus`.

4) Update `decisions.md` when applicable
- Add entries only for meaningful decisions.
- Include: context, options considered, decision, rationale, consequences.

5) Update `bugs.md` when applicable
- Add entries for bug fixes from this scope.
- Include: symptom, root cause, fix, prevention, files.

6) Update `patterns.md` when applicable
- Add reusable patterns discovered in this scope.
- Include: use when, implementation, example, gotchas.

7) Quality checks
- Keep `.claude/memory/active.yaml` small (target <= 60 lines).
- Include affected file paths in memory entries.
- Avoid speculation and future tense.
- Keep memory files high-signal and brief.

Output:
- Print a short summary of `active.yaml` updates plus archive files updated.
- Call out if no durable archive updates were needed.
