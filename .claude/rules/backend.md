# Backend Rules

## Scope
Applies when editing backend implementation under `app/**`.

## Standards
- Maintain repository -> service -> API boundary.
- Validate all external input at service/API boundaries.
- Use strict typing and explicit return types.
- Handle async operations with timeouts and explicit error handling.
- Avoid direct DB access outside repositories.

## Verification
- Run targeted tests for changed behavior.
- Keep lint/typecheck clean for touched files.

## References
- `.claude/CLAUDE.md` for full Python stack patterns.
- `.claude/constitution.md` for immutable project rules.

