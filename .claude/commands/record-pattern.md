Purpose:
Record a reusable implementation pattern in shared project memory.

Target Files:
- `.claude/memory/active.yaml` (update `patterns_active`)
- `.claude/memory/patterns.md`

Inputs:
- Pattern name from command arguments: `$ARGUMENTS`
- If no arguments are provided, ask for a short pattern name.

Steps:

1) Collect pattern scope
- Review recent/staged changes and related files.
- Identify where this pattern was applied.

2) Append a pattern entry to `patterns.md`
- Use heading format: `## [Pattern Name]`
- Include:
  - **Use When**
  - **Implementation**
  - **Example**
  - **Gotchas**
  - **Files** (where used)

3) Update `active.yaml`
- Add/update a short pattern pointer under `patterns_active`.
- Keep only currently useful patterns (avoid long historical list).

4) Quality checks
- Record only patterns likely to repeat.
- Keep instructions actionable and brief.
- Avoid one-off task notes that belong in `context.md`.
- Keep `active.yaml` compact (summary-only).

Output:
- Confirm pattern was recorded in `active.yaml` and `patterns.md`.
- Show pattern name and files captured.
