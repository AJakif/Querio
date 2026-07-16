# Core Rules (Always On)

## Planning and Execution
- Use a plan for multi-file or ambiguous tasks.
- Prefer small, testable increments.
- For behavior changes, add or update tests.

## Memory and Documentation
- Keep `.claude/memory/active.yaml` concise and current (always-loaded memory).
- Record durable decisions in `.claude/memory/decisions.md`.
- Record root-cause bug fixes in `.claude/memory/bugs.md`.
- Record reusable implementation patterns in `.claude/memory/patterns.md`.
- Use `.claude/memory/context.md` for expanded session context when needed.

## Security and Safety
- Never expose or request secrets from `.env`, key files, or credentials folders.
- Follow repository security and architecture constraints in `.claude/constitution.md`.

## Token Discipline (canonical)
This project pays ~5× more for output than input; the always-loaded prefix is taxed every turn. Be deliberate.
- Don't paste long logs/files into chat; save to a file, reference `@path`, read on demand.
- Keep the always-loaded prefix (`CLAUDE.md`, this file, `active.yaml`) small AND stable — any change busts the cross-session cache (cached input ≈ 0.1× uncached). Batch prefix edits.
- Inter-agent handoffs pass scratch-file **paths**, not contents: `.claude/scratch/<task-id>/{plan,diff-summary,review}.md`.

### Output registers
**Golden rule (evidence-based): compress the _report_, never the _reasoning/findings_.** Terse output is ~free; compressing the model's *thinking* (forced JSON, short-path, caveman-on-reasoning) costs ~10–15% correctness on code. Trim prose, never steps / findings / `file:line` / diffs. Pick a register by role:
- **terse-professional** — default; user-facing replies + reasoning agents (`architect-opus`, `debugger-buddy`). **Minimal by default:** result/verdict first, then only load-bearing content — key bullets, `file:line`, blockers; drop preamble, filler, restating the ask, and recaps of what you just did. Emit a section only when it carries decision-relevant content. Fragments + symbols over sentences. **Reason fully, report tersely.** Expand to full prose/sections ONLY when the user asks (explain / why / details) or it's load-bearing (blocker, security/correctness, design tradeoff). No model-signature trailer (`_Agent | Model_`) or ritual tag scaffolding in user-facing replies — keep substantive confidence tags only where they change how much to trust a claim.
- **telegraphic** — mechanical agents (`builder-sonnet`, `critic-opus`, `bug-fixer-sonnet`, `python-reviewer`, `writer-haiku`) + ALL inter-agent handoffs. Caveman-lite: drop articles + filler + preamble; max symbols/fragments; **diff-only for code** (never re-emit unchanged code); ≤300 words; scratch-file **paths** not contents; no empty sections. Findings / `file:line` / diffs stay exact — terseness is prose-only.
- Opus agents cap at 4000 output tokens → overflow to `.claude/scratch/<task-id>/<agent>-overflow.md`.
