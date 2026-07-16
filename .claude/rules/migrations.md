# Migration Rules

## Scope
Applies when editing `alembic/**` and schema-related backend code.

## Rules
- Keep one logical schema change per migration when possible.
- Include safe downgrade paths unless explicitly not supported.
- Validate migration assumptions against current models.
- Note any contract or data-impacting changes in changelog/docs.

## Safety
- Do not modify existing production migrations without explicit approval.
- Treat data migrations as high-risk and document rollback strategy.

