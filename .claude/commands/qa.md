Purpose:
Risk-based QA pass: test strategy → run suite → coverage/gap audit against acceptance criteria → release-readiness verdict, using qa-lead-sonnet. Enforces load-bearing tests in BOTH directions (missing coverage AND ceremonial over-testing).

Input:
- `$ARGUMENTS`: Scope — a feature, a diff/branch, an acceptance-criteria set, or a bug to reproduce. If empty, scope to uncommitted changes (`git diff --name-only`).

Steps:

1) Determine scope + load criteria
- Resolve the files/feature under test. Read the acceptance criteria if a `product-brief.md` exists for this task; otherwise derive intended behavior from the spec/plan/diff.
- Read the relevant `.claude/domains/<domain>.md` (Module Map) — its **Tests** line names what's worth covering.

2) Spawn qa-lead-sonnet
The QA lead runs: risk map (likelihood × blast-radius; security/authz/tenancy/billing/migrations are high by default) → plan (the single most load-bearing test per top risk and per AC, marked exists/missing/weak) → reproduce any bug deterministically → run the relevant suite (honor `dev_test_infra_blockers.md` Docker quirks) and report real output → verdict.
- QA applies the `.claude/rules/testing.md` Load-Bearing Filter + Ban List + budget. It flags BOTH gaps and trivial/redundant tests for deletion. It does NOT write test code.

3) Close gaps (conditional)
- If the QA report names missing load-bearing tests, route to `builder-sonnet` to author exactly those (builder enforces the testing budget), then re-run to confirm green.
- If it flags ceremonial/Ban-List tests, surface the concrete deletion list (do not delete pre-existing tests as a side effect — `FOLLOW-UP:` per testing.md scope rule).

4) Bug triage handoff
- A confirmed repro routes to `debugger-buddy` (root cause) or `bug-fixer-sonnet` (obvious cause) — one bug, one regression test.

5) Present results
- Risk map + per-AC coverage status, suite result (real counts), gaps closed, over-testing flagged, and the release-readiness verdict: RELEASE-READY / NOT-READY / CONDITIONAL with concrete gating items.

Inter-agent handoff: QA report is written to `.claude/scratch/<task-id>/qa-report.md`; pass the path forward, not the contents. Docs → writer-haiku.
