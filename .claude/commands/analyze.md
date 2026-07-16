Purpose:
Deep analysis of a requirement, problem, or architectural question using architect-opus with the full RADAR-enhanced methodology.

Input:
- `$ARGUMENTS`: Problem statement, requirement, or architectural question

Steps:

1) Load context
Read the following for project context:
- `architecture/system-model.yaml`
- `.claude/CHANGELOG_AI.md`
- `.claude/memory/active.yaml`
- Any files referenced in the arguments

2) Spawn architect-opus
Pass the problem/requirement with full project context.
The architect executes the enhanced analysis protocol:
- Problem understanding with epistemic standards (confidence tags)
- Landscape research: existing solutions, libraries, SaaS, patterns (library-first)
- 3 distinct approaches with pairwise comparison (bias elimination)
- Steel-manned recommendation with pre-mortem
- Spec + implementation plan with parallelized tasks

3) Present results
Show the architect's analysis and plan.
Ask the user: "Ready to implement? Say yes to proceed, or provide feedback to refine."

4) If user approves, transition to /implement with the produced plan.
