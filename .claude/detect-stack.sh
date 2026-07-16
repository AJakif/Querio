#!/bin/bash
# detect-stack.sh - Detect project stack and optionally initialize CLAUDE.md
#
# Usage:
#   ./detect-stack.sh [directory]           # Just detect
#   ./detect-stack.sh [directory] --init    # Detect and initialize

set -e

DIR="${1:-.}"
INIT="${2:-}"

detect_stack() {
    local dir="$1"
    
    # Check for TypeScript/JavaScript
    if [[ -f "$dir/package.json" ]]; then
        if grep -q '"typescript"' "$dir/package.json" 2>/dev/null || \
           [[ -f "$dir/tsconfig.json" ]]; then
            echo "typescript"
            return
        else
            echo "javascript"
            return
        fi
    fi
    
    # Check for Python
    if [[ -f "$dir/pyproject.toml" ]] || \
       [[ -f "$dir/requirements.txt" ]] || \
       [[ -f "$dir/setup.py" ]] || \
       [[ -f "$dir/Pipfile" ]]; then
        echo "python"
        return
    fi
    
    # Check for Go
    if [[ -f "$dir/go.mod" ]]; then
        echo "go"
        return
    fi
    
    # Check for Rust
    if [[ -f "$dir/Cargo.toml" ]]; then
        echo "rust"
        return
    fi
    
    # Check for .NET
    if ls "$dir"/*.csproj 1>/dev/null 2>&1 || \
       ls "$dir"/*.sln 1>/dev/null 2>&1 || \
       ls "$dir"/**/*.csproj 1>/dev/null 2>&1; then
        echo "dotnet"
        return
    fi
    
    echo "unknown"
}

STACK=$(detect_stack "$DIR")

if [[ "$INIT" == "--init" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    echo "=== Claude Workflow Initialization ==="
    echo "Directory: $DIR"
    echo "Detected Stack: $STACK"
    echo ""
    
    if [[ "$STACK" == "unknown" ]]; then
        echo "⚠️  Could not detect stack. Please manually create CLAUDE.md"
        exit 1
    fi
    
    # Copy base CLAUDE.md
    if [[ -f "$DIR/CLAUDE.md" ]]; then
        echo "⚠️  CLAUDE.md already exists. Skipping."
    else
        cp "$SCRIPT_DIR/CLAUDE.md" "$DIR/CLAUDE.md"
        echo "" >> "$DIR/CLAUDE.md"
        echo "---" >> "$DIR/CLAUDE.md"
        echo "" >> "$DIR/CLAUDE.md"
        cat "$SCRIPT_DIR/STACKS/${STACK}.claude.md" >> "$DIR/CLAUDE.md"
        echo "✅ Created CLAUDE.md with $STACK configuration"
    fi
    
    # Copy constitution if not exists
    if [[ -f "$DIR/constitution.md" ]]; then
        echo "⚠️  constitution.md already exists. Skipping."
    else
        cp "$SCRIPT_DIR/TEMPLATES/constitution.md" "$DIR/constitution.md"
        echo "✅ Created constitution.md"
    fi
    
    # Create docs directory
    mkdir -p "$DIR/docs"
    if [[ ! -f "$DIR/docs/ARCHITECTURE.md" ]]; then
        echo "# Architecture" > "$DIR/docs/ARCHITECTURE.md"
        echo "" >> "$DIR/docs/ARCHITECTURE.md"
        echo "TODO: Document your system architecture here." >> "$DIR/docs/ARCHITECTURE.md"
        echo "✅ Created docs/ARCHITECTURE.md"
    fi
    
    echo ""
    echo "=== Next Steps ==="
    echo "1. Edit CLAUDE.md and fill in {{PLACEHOLDER}} values"
    echo "2. Edit constitution.md with your project's rules"
    echo "3. Document architecture in docs/ARCHITECTURE.md"
    echo ""
    echo "Then start Claude Code:"
    echo "  cd $DIR"
    echo "  claude --model opus 'Help me plan a new feature'"
else
    echo "$STACK"
fi
