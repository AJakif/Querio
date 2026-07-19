"""Shared prompt assembly for Planner, SqlGenerator, and Aggregator.

Fixed, cache-friendly message order per Design Delta v1.0 T3:
  1. STATIC PREFIX  — byte-identical across all three agents
                      (system identity + shared rules + optional schema block)
  2. AGENT-SPECIFIC INSTRUCTIONS  — each agent's __init__ appends its own block
  3. DYNAMIC STATE  — assembled per-request via ``build_dynamic_state``
                      (session brief [T9b slot] → question → runtime data)

Both functions are pure: no I/O, no pydantic_ai dependency.
"""


_SHARED_IDENTITY = (
    "You are an AI assistant operating as part of a read-only PostgreSQL analytics pipeline."
)

_SHARED_RULES = """\
Core rules that apply to every agent in this pipeline:
- Ground every output in real data. Never fabricate schema objects, column names, values, \
or claims not present in the data you receive.
- This is a read-only analytics system. Never produce or suggest write or administrative \
database operations.
- Never restate prior LLM-generated prose as established fact when reasoning about user \
questions. Reason only from the structured inputs provided to you."""


def build_static_prefix(schema_block: str = "") -> str:
    """Return the byte-identical static prefix shared by all three agents.

    Args:
        schema_block: Optional pre-fetched schema text (default ``""``).
            Today's agents pass empty — schema arrives via the on-demand ``get_schema``
            tool at runtime.  The slot is reserved here for future static embedding (T9b).

    Returns:
        Deterministic string: identity + shared rules [+ ``Schema:`` section when
        *schema_block* is truthy].  Calling with the same argument always returns an
        identical byte sequence — suitable for provider prompt-cache hits.
    """
    parts = [_SHARED_IDENTITY, _SHARED_RULES]
    if schema_block:
        parts.append(f"Schema:\n{schema_block}")
    return "\n\n".join(parts)


def build_dynamic_state(
    session_brief: str,
    question: str,
    runtime_data: str = "",
) -> str:
    """Assemble the per-request dynamic state block passed as the user message.

    Order (Design Delta v1.0):
      1. *session_brief*  — T9b slot; pass ``""`` until session-brief feature is built.
      2. ``Question: {question}``
      3. *runtime_data*   — agent-specific payload (plan JSON, result rows, etc.);
                            omitted when empty.

    Empty sections are omitted so the user message stays concise.

    Args:
        session_brief: Reserved T9b slot.  Pass ``""`` today.
        question: The user's natural-language question.
        runtime_data: Agent-specific runtime payload (plan context, rows, etc.).

    Returns:
        A single string with sections joined by blank lines.
    """
    parts: list[str] = []
    if session_brief:
        parts.append(session_brief)
    parts.append(f"Question: {question}")
    if runtime_data:
        parts.append(runtime_data)
    return "\n\n".join(parts)
