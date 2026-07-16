#!/bin/bash
# init-memory.sh - Initialize project memory structure (lean hybrid model)
#
# Usage: ./init-memory.sh [project-directory]

set -euo pipefail

DIR="${1:-.}"
cd "$DIR"

echo "=== Initializing Project Memory ==="
echo "Directory: $(pwd)"

mkdir -p .claude/memory

if [[ ! -f .claude/memory/active.yaml ]]; then
    cat > .claude/memory/active.yaml <<'EOF'
version: 1
updated: "YYYY-MM-DD"

current_focus:
  - "Initial setup"

recent_changes:
  - "Project memory initialized"

open_blockers: []
decisions_recent: []
bugs_open: []
patterns_active: []

next_steps:
  - "Replace placeholders in active.yaml"
EOF
    echo "[ok] Created .claude/memory/active.yaml"
fi

if [[ ! -f .claude/memory/context.md ]]; then
    cat > .claude/memory/context.md <<'EOF'
# Project Context

> Detailed context archive. Keep active, always-loaded state in `.claude/memory/active.yaml`.

## Current Focus
- [ ] Initial setup

## Recent Changes
- Project memory initialized

## Blocked/Pending
- None

## Notes
- 
EOF
    echo "[ok] Created .claude/memory/context.md"
fi

if [[ ! -f .claude/memory/decisions.md ]]; then
    cat > .claude/memory/decisions.md <<'EOF'
# Architecture Decisions

> Detailed decision archive. Keep only recent decision pointers in `.claude/memory/active.yaml`.

<!-- Format:
## YYYY-MM-DD: [Decision Title]
- **Context**: [What problem we faced]
- **Options**: [What we considered]
- **Decision**: [What we chose]
- **Rationale**: [Why]
- **Consequences**: [Trade-offs accepted]
- **Files**: [Affected files]
-->
EOF
    echo "[ok] Created .claude/memory/decisions.md"
fi

if [[ ! -f .claude/memory/bugs.md ]]; then
    cat > .claude/memory/bugs.md <<'EOF'
# Bug Fixes & Solutions

> Detailed bug archive. Keep open/high-priority bug pointers in `.claude/memory/active.yaml`.

<!-- Format:
## [Bug Title]
- **Symptom**: [What went wrong]
- **Root Cause**: [Why it happened]
- **Fix**: [How we solved it]
- **Prevention**: [How to avoid in future]
- **Files**: [Affected files]
-->
EOF
    echo "[ok] Created .claude/memory/bugs.md"
fi

if [[ ! -f .claude/memory/patterns.md ]]; then
    cat > .claude/memory/patterns.md <<'EOF'
# Discovered Patterns

> Detailed pattern archive. Keep active pattern pointers in `.claude/memory/active.yaml`.

<!-- Format:
## [Pattern Name]
- **Use When**: [Trigger condition]
- **Implementation**: [How to do it]
- **Example**: [Code snippet]
- **Gotchas**: [Watch out for]
- **Files**: [Where used]
-->
EOF
    echo "[ok] Created .claude/memory/patterns.md"
fi

if [[ -f CLAUDE.md ]]; then
    if ! grep -q "@.claude/memory/active.yaml" CLAUDE.md; then
        {
            echo ""
            echo "## Project Memory"
            echo "@.claude/memory/active.yaml"
        } >> CLAUDE.md
        echo "[ok] Added active memory import to CLAUDE.md"
    else
        echo "[info] CLAUDE.md already imports active.yaml"
    fi
else
    echo "[info] No root CLAUDE.md found; create one and import @.claude/memory/active.yaml"
fi

if [[ -f .gitignore ]] && ! grep -q "^CLAUDE.local.md$" .gitignore; then
    {
        echo ""
        echo "# Claude local files (optional)"
        echo "CLAUDE.local.md"
    } >> .gitignore
    echo "[ok] Updated .gitignore with CLAUDE.local.md"
fi

echo ""
echo "=== Memory System Initialized ==="
echo "Structure:"
echo ".claude/memory/active.yaml   (always-loaded, compact)"
echo ".claude/memory/context.md    (detailed context archive)"
echo ".claude/memory/decisions.md  (decision archive)"
echo ".claude/memory/bugs.md       (bug archive)"
echo ".claude/memory/patterns.md   (pattern archive)"
echo ""
echo "Next steps:"
echo "1. Update active.yaml with current focus"
echo "2. Use /update-memory at end of meaningful sessions"
