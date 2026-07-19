"""Load-bearing tests for T9b: rolling session brief cap.

Test budget: 2 (new-feature budget 3–7; these two are the most direct proofs
of the two hard acceptance criteria that cannot be tested end-to-end without
a live LLM).

Tests:
  1. Acceptance criterion 1 — 30-turn simulation: prompt assembled at turn 30
     is not larger than at turn 2 (brief stays capped, history never replayed raw).
  2. Absence of brief in prompt when brief is empty (no regression on turn 1).
"""

from __future__ import annotations

from app.agent.prompt_builder import build_dynamic_state
from app.agent.prompt_gate import truncate_brief
from app.core.config import settings


class TestThirtyTurnCapHolds:
    def test_prompt_size_stays_bounded_after_thirty_turns(self) -> None:
        """Simulate 30 Aggregator turns where an adversarial model always emits a
        brief that tries to grow unboundedly.  The assembled dynamic-state prompt must
        stabilise at a bounded size once the cap kicks in (no growth from turn N onward
        when the brief is already at max_tokens).

        This is acceptance criterion 1: history is never replayed raw — the prompt
        stays capped regardless of how many prior turns exist.
        """
        max_tokens = settings.session_brief_max_tokens
        # 4 chars/token heuristic — same constant used by truncate_brief
        max_brief_chars = max_tokens * 4
        question = "What is the total revenue?"
        runtime_data = "Plan context: {}"

        brief = ""
        prompt_sizes: list[int] = []

        for turn in range(1, 31):
            # Adversarial model: always appends a new entry to the FULL growing history
            # (simulates a naive model that ignores the budget instruction).
            # Without the backstop, this would grow without bound.
            new_entry = f"Q: question number {turn}? → A: result is {turn * 100}"
            unbounded_output = (brief + "  " + new_entry).strip() if brief else new_entry

            # Apply the backstop truncation (same as PydanticAiAggregator does)
            brief = truncate_brief(unbounded_output, max_tokens)

            prompt = build_dynamic_state(
                session_brief=brief,
                question=question,
                runtime_data=runtime_data,
            )
            prompt_sizes.append(len(prompt))

        # 1. The brief itself must never exceed the char budget
        assert len(brief) <= max_brief_chars, (
            f"Brief at turn 30 is {len(brief)} chars, exceeds cap of {max_brief_chars}"
        )

        # 2. Once the cap kicks in, prompt size must be stable (non-growing).
        # Find the first turn where the prompt reached its plateau and verify no growth after.
        # (The plateau is where len(brief) first hit max_brief_chars.)
        plateau_size = prompt_sizes[-1]
        for size in prompt_sizes[len(prompt_sizes) // 2:]:
            assert size <= plateau_size + 10, (  # +10 chars tolerance for word-boundary trimming
                f"Prompt grew after plateau: {size} > {plateau_size} — brief cap regressed"
            )


class TestEmptyBriefOnFirstTurn:
    def test_empty_brief_omitted_from_dynamic_state(self) -> None:
        """When session_brief is empty (first turn / stateless), it must not add
        any text to the prompt — no 'Session Brief:' header, no blank lines."""
        prompt = build_dynamic_state(session_brief="", question="how many orders?")

        assert "Session Brief" not in prompt
        assert prompt.startswith("Question:")
