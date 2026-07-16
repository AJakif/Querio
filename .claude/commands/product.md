Purpose:
Product discovery → prioritization → scoped spec with acceptance criteria, using product-strategist-opus. Decides WHAT to build and WHY before any technical design. Feeds /analyze and /feature.

Input:
- `$ARGUMENTS`: A product idea, problem statement, feature request, or "prioritize: <list>". Optional context after a `---` separator (data, constraints, existing docs).

Steps:

1) Load context
- `.claude/memory/active.yaml` (current focus / what's already shipped or gated-off), `architecture/architecture-compact.md`, and any domain doc(s) the idea touches (Module Map in root `CLAUDE.md`).
- Any files referenced in the arguments.

2) Spawn product-strategist-opus
Pass the idea + context. The strategist runs: frame (user · pain · why now) → ground in what exists → discovery (users, JTBD, success metric, constraints, non-goals) → prioritize (RICE / value-vs-effort; effort is an assumption until architect sizes it) → scope the smallest releasable slice → acceptance criteria (happy / off / error per actor) → pre-mortem for DEEP.

3) Present the brief
Show the recommendation (build / don't / cut / sequence), the scoped slice, and the acceptance criteria. Ask: "Ready to design + build? Say yes for /analyze, or give feedback to refine."

4) Author the artifact (on request)
If the user wants a written deliverable, route to `writer-haiku`:
- Single Scrum story → use the `/user-story` format.
- PRD → `/to-prd`. Formal requirements → `/spec-requirements`.
Provenance marker required on every Markdown artifact.

5) Handoff
On approval, transition to `/analyze` (architect-opus designs the HOW) or `/feature` (full build pipeline). The acceptance criteria become the contract `qa-lead-sonnet` later verifies against — carry them forward.

Inter-agent handoff: product brief is written to `.claude/scratch/<task-id>/product-brief.md`; pass the path forward, not the contents.
