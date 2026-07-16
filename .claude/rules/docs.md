# Documentation Rules

## Scope
Applies when editing `docs/**` and architecture/changelog artifacts.

## Rules
- Keep docs factual and aligned with code in this branch.
- Avoid future-tense speculation in status docs.
- Update architecture/changelog when interfaces, schema, or flows change.
- Prefer short sections and actionable checklists.
- Route Markdown authoring to `writer-haiku` by default unless the human explicitly overrides.
- Include provenance marker on writer-authored docs:
  `<!-- written-by: writer-haiku | model: haiku -->`

## References
- `.claude/commands/update-summary.md` for architecture update procedure.
- `.claude/commands/verify-writing.md` for provenance checks.
