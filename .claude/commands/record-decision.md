Purpose:
Record a significant decision in shared project memory.

Target Files:
- `.claude/memory/active.yaml` (update `decisions_recent`)
- `.claude/memory/decisions.md`

Inputs:
- Decision topic from command arguments: `$ARGUMENTS`
- If no arguments are provided, ask for a short decision title.

Steps:

1) Collect decision context
- Check staged diff first: `git diff --staged --name-only`
- If empty, use last commit: `git show --name-only --pretty=""`
- Infer affected files and relevant context.

2) Append a new decision entry to `decisions.md`
- Use heading format: `## YYYY-MM-DD: [Decision Title]`
- Include:
  - **Context**
  - **Options**
  - **Decision**
  - **Rationale**
  - **Consequences**
  - **Files** (affected paths)

3) Update `active.yaml`
- Add or refresh an item under `decisions_recent` with:
  - stable id
  - short decision summary
  - ref to `.claude/memory/decisions.md`
- Keep only the most recent, high-value items.

4) Quality checks
- Keep it concise and factual.
- Record only meaningful, durable decisions.
- Avoid speculative language.
- Keep `active.yaml` compact (summary, not full detail).

Output:
- Confirm decision was recorded in both `active.yaml` and `decisions.md`.
- Show decision title and affected files captured.
