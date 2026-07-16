Purpose:
Keep architecture documentation and CHANGELOG_AI.md up to date using recent code changes, without re-analyzing the entire repo.

Architecture Files:
- `architecture/system-model.yaml` - Machine-readable complete model (primary context for AI)
- `architecture/architecture-compact.md` - Bullet-only quick reference
- `architecture/architecture-summary.md` - High-level human-readable overview
- `.claude/CHANGELOG_AI.md` - Implementation history

Inputs:
- Prefer staged changes.
- If nothing is staged, use the last commit.
- If both are unavailable, ask for a target branch or feature name and use git diff against main.

Steps:

1) Detect scope of change
- Use: git diff --staged --name-only
- If empty, use: git show --name-only --pretty=""
- Identify affected domains: API, DB/migrations, services, repositories, agents, aggregators, auth, admin, config.

2) Update CHANGELOG_AI.md
Add a new entry under "Unreleased" with:
- Date
- Feature/phase name (infer from branch name or ask if unclear)
- What changed (3 to 8 bullets)
- Key files created/modified
- Contract changes (API endpoints, DB migrations, env vars)
- Architecture updates (patterns, dependencies, flows)

3) Update system-model.yaml (primary)
Only edit sections impacted by the change:
- `services.*` - Add/update service entries with status and methods
- `api.groups.*` - Update endpoint counts and lists
- `data_stores.postgres.tables` - Add new tables
- `auth.*` - Update auth methods or scopes
- `config.*` - Update weights, thresholds, or escalation rules
- `orchestrator.*` - Update nodes or routing
- `implementation_status.*` - Move items between complete/stub
- `directory_structure.*` - Add new files/directories

4) Update architecture-compact.md (if significant change)
Only update for:
- New services or major method changes
- New API endpoint groups
- New data stores or tables
- Auth model changes
- New evaluation modes or thresholds
- Exception hierarchy changes

5) Update architecture-summary.md (rarely)
Only update for:
- Major new features affecting core flow
- Stack changes
- Significant implementation status changes

6) Consistency checks
- Ensure names match code (service names, endpoints, table names)
- No speculation, no future tense
- Keep YAML valid (test with: python -c "import yaml; yaml.safe_load(open('architecture/system-model.yaml'))")
- No duplicated content across files

Output:
- Print a short summary of what you updated and which files/sections changed.
- If YAML was modified, confirm it validates.
