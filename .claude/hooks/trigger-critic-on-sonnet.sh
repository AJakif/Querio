#!/usr/bin/env bash
#
# trigger-critic-on-sonnet.sh — DISABLED 2026-06-09 (no longer registered).
#
# WHAT THIS WAS
# -------------
# A SubagentStop hook intended to enforce the Auto-Review Policy
# (.claude/AGENTS.md): after a builder-sonnet / bug-fixer-sonnet subagent
# finished, inject an instruction telling the PARENT agent to spawn critic-opus.
#
# WHY IT WAS REMOVED (root cause of the infinite-loop / runaway behaviour)
# -----------------------------------------------------------------------
# The mechanism is incompatible with how SubagentStop actually works
# (https://code.claude.com/docs/en/hooks):
#   * A SubagentStop hook that returns `hookSpecificOutput.additionalContext`
#     (or a block decision) does NOT hand an instruction to the parent — it
#     PREVENTS THE STOPPING SUBAGENT FROM STOPPING and feeds the text back into
#     that same subagent so it "continues". The injected "spawn critic-opus, do
#     not complete, do not report" text therefore traps the builder-sonnet
#     subagent: every attempt to stop re-fires the hook and re-injects, so it
#     can never terminate. (Observed: a subagent burned its whole turn trying to
#     escape this and ended up editing the hook + widening permissions.)
#   * The script also keyed off a non-existent `CLAUDE_SUBAGENT` env var in an
#     attempted guard; Claude Code exposes subagent identity via the JSON input
#     fields `agent_id` / `agent_type`, not an env var, so that guard would have
#     silently disabled the hook entirely.
#
# CURRENT STATE
# -------------
# The SubagentStop registration has been removed from .claude/settings.json, so
# this script is no longer invoked. Auto-review remains a *convention* the main
# agent follows (AGENTS.md §Auto-Review Policy): spawn critic-opus after an
# implementation. This file is retained only as a pure pass-through no-op and as
# documentation — if it is ever re-registered it will do nothing and cannot loop.
#
# CORRECT WAY TO HARD-ENFORCE THIS (if desired, as a future task)
# ---------------------------------------------------------------
# Use a PostToolUse hook matched to the `Task` tool. PostToolUse fires in the
# PARENT context after a Task subagent returns, its additionalContext is added
# to the parent (it does not block a stop), and it does not loop: the follow-up
# critic-opus Task fires PostToolUse again with agent_type=critic-opus, which the
# script skips. The script must inspect tool_input.subagent_type to decide.

# Pure pass-through. Read and discard stdin so a writing pipe never blocks. Exit 0.
cat >/dev/null 2>&1 || true
exit 0
