<!-- written-by: writer-haiku | model: haiku -->
Purpose:
AI code review gate for Stage 4 of the spec-driven development workflow.
Verifies that the implementation covers all acceptance criteria, follows codebase patterns,
and introduces no security issues or scope creep. Run before opening a PR.

Follows Stage 4 (Code Review Gate 1) of project_docs/spec-driven-development-workflow.md.

Input:
- `$ARGUMENTS`: Path to the approved spec file.
  Example: /spec-stage4-review project_docs/billing-audit.spec.md

---

Pipeline:

0) DELTA-ONLY CHECK

Before running the full review:
1. Read `.claude/scratch/<spec-name>/last-review.json` if it exists.
2. If it contains `{"branch": <current branch>, "head_sha": <git rev-parse HEAD>, "verdict": "APPROVED"}`:
   - Run a **delta-only review**: skip Part D (Architecture Compliance) and Part E (Security Scan).
   - Run only Parts A (BDD coverage), B (NFR compliance), C (scope creep) on commits since the recorded SHA.
   - If no new commits, emit `DELTA: NO-OP — already approved at <sha>` and exit.
3. Otherwise, run the full Parts A-F as before.

After completing the review (full or delta), write the result to `.claude/scratch/<spec-name>/last-review.json` with the current branch, HEAD SHA, and final verdict.

1) LOAD CONTEXT

Read:
- The spec file at $ARGUMENTS (required)
- `architecture/system-model.yaml`
- `.claude/memory/active.yaml`

Run: `git diff main...HEAD --name-only` to get the list of changed files in this branch.
Read each changed file.

If $ARGUMENTS is empty, stop and tell the user:
"Please provide the path to the spec file. Example: /spec-stage4-review project_docs/my-feature.spec.md"

---

2) REVIEW (critic-opus)

Spawn critic-opus with the spec and all changed files:

  "You are performing a spec compliance review. Verify that the implementation matches the spec.

  Spec: [spec-path]
  Changed files: [list from git diff]

  PART A: ACCEPTANCE CRITERIA COVERAGE
  For each BDD scenario in the spec:
  - Find the corresponding test(s) in the changed files.
  - Verify the test asserts the Given/When/Then conditions (not just that it runs).
  - Status: COVERED | PARTIAL (test exists but incomplete assertion) | MISSING

  PART B: NFR COMPLIANCE
  For each NFR in the spec:
  - How is the threshold enforced? (code guard, test assertion, or not enforced)
  - Status: ENFORCED | PARTIAL | NOT ENFORCED

  PART C: SCOPE COMPLIANCE
  Is there any code in the diff NOT required by any spec requirement?
  Flag each instance as SCOPE CREEP: [file:line] [description].

  PART D: ARCHITECTURE COMPLIANCE
  - Does code follow repository → service → API layer pattern?
  - Are type hints complete? (no untyped Any without justification)
  - Are async operations handled with timeouts and explicit error handling?
  - Is database access isolated to repositories?

  PART E: SECURITY SCAN
  - SQL injection risk
  - Unvalidated input passed to queries or system calls
  - Hardcoded secrets or credentials
  - Missing authentication or authorization on any new endpoint
  - OWASP top 10 concerns

  PART F: DESIGN ALIGNMENT
  - Does the implementation match the 'Design Validation' section of the spec?
  - Are all ✓ (confirmed) design decisions implemented as described?
  - Are all ⚠ (flagged) concerns addressed in code?

  Final VERDICT: APPROVED | NEEDS FIXES

  List every issue with:
  Severity: CRITICAL (block merge) | HIGH | MEDIUM | LOW
  Format: [Severity] | [Category] | [File:line] | [Description] | [Required fix]"

---

3) FIX (builder-sonnet — if CRITICAL or HIGH issues found)

For each CRITICAL or HIGH finding:
- Spawn builder-sonnet to fix the issue
- Re-run critic-opus to verify the fix
- Repeat until APPROVED verdict

---

4) REPORT

Present to the user:
- Acceptance criteria coverage table (COVERED / PARTIAL / MISSING per scenario)
- NFR compliance table
- Scope creep findings (if any)
- Security scan summary
- Final verdict

If APPROVED, print this PR readiness checklist:
  PR READINESS CHECKLIST:
  - [ ] Open PR — attach spec file path in PR description
  - [ ] Add label `ai-generated-pr` if >80% of code was AI-generated
  - [ ] Add label `focus-review:architecture` for human reviewer attention
  - [ ] Human reviewer: verify design alignment, check for unstated assumptions
  - [ ] Confirm all CI tests pass
  - [ ] Tech lead signs off on spec acceptance criteria in ClickUp
  - [ ] Merge only after all acceptance criteria pass
