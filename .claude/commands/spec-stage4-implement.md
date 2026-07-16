<!-- written-by: writer-haiku | model: haiku -->
Purpose:
Spec-driven TDD implementation for Stage 4 of the spec-driven development workflow.
Reads a .spec.md file and implements all requirements using test-first development.
Every BDD acceptance criterion must have a passing test before implementation is complete.

Follows Stage 4 of project_docs/spec-driven-development-workflow.md.

Input:
- `$ARGUMENTS`: Path to the approved spec file.
  Example: /spec-stage4-implement project_docs/billing-audit.spec.md

---

Pipeline:

1) LOAD CONTEXT

Read:
- The spec file at $ARGUMENTS (required)
- `architecture/system-model.yaml`
- `.claude/CHANGELOG_AI.md`
- `.claude/memory/active.yaml`

Extract from the spec:
- All EARS functional requirements (REQ-001, REQ-002, ...)
- All BDD acceptance scenarios (Given / When / Then)
- Non-functional requirement thresholds (latency, security, availability)
- Design overview and design validation sections

If $ARGUMENTS is empty, stop and tell the user:
"Please provide the path to the approved spec file. Example: /spec-stage4-implement project_docs/my-feature.spec.md"

---

2) PLAN (architect-opus)

Spawn architect-opus:

  "Read the spec file carefully. Produce an implementation plan.

  A) COMPONENT MAP
  For each requirement, identify what must be created or modified:
  - Database: new tables, columns, indices, migrations needed
  - Models: new or modified SQLAlchemy models
  - Repositories: new or modified repository methods
  - Services: new or modified service methods
  - API: new or modified endpoints
  - Tests: which BDD scenarios map to unit vs integration tests

  B) DEPENDENCY ORDER
  Order by dependency: database → models → repositories → services → API → tests.
  Identify independent groups that can be built in parallel.

  C) TDD SEQUENCE
  For each BDD scenario:
  - Scenario ID and title
  - Test type: unit or integration
  - Component the test lives in
  - What fixtures or mocks are needed
  - Expected RED assertion (what the failing test checks)

  D) RISK FLAGS
  Any implementation risk not covered by the spec (migration safety, concurrency, external service dependencies).

  Read the spec file and system-model.yaml. Return the full plan."

---

3) APPROVE

Present the architect's plan to the user.
Wait for explicit user approval before proceeding to implementation.
If feedback is given, loop back to architect-opus with the feedback.

---

4) IMPLEMENT (builder-sonnet — parallel where component groups are independent)

For each independent component group from the architect's plan, spawn builder-sonnet:

  "Implement [component group] according to the spec at [spec-path].

  Follow TDD strictly per group:
  - RED: Write the test first. It must fail for the right reason before writing code.
  - GREEN: Write the minimum code to make the test pass.
  - REFACTOR: Clean up without breaking tests.

  For every BDD scenario assigned to this group, there must be a corresponding pytest test.
  Every NFR with a measurable threshold must have an assertion in the relevant test.

  Codebase patterns to follow:
  - Repository pattern: app/repositories/
  - Service pattern: app/services/
  - FastAPI endpoints: app/api/v1/
  - Async SQLAlchemy: app/db/

  Do not implement anything not required by the spec.
  If you encounter an ambiguity, stop and flag it — do not guess."

Wait for all parallel builders to complete before proceeding.

---

5) REVIEW (critic-opus — automatic)

Spawn critic-opus:

  "Review the implementation against the spec at [spec-path].

  Verify:
  1. Every EARS requirement (REQ-XXX) has implementation code.
  2. Every BDD scenario has a passing pytest test.
  3. Every NFR threshold is asserted in a test or enforced in code.
  4. No scope creep: no code exists that is not required by the spec.
  5. Architecture compliance with system-model.yaml patterns.
  6. Security: no injection, no unvalidated input, no hardcoded secrets.

  For each BDD scenario report:
  - COVERED: test exists and asserts the Given/When/Then conditions
  - PARTIAL: test exists but does not fully assert the conditions
  - MISSING: no test found

  Issue CRITICAL if any acceptance criterion has no test."

If CRITICAL issues found → spawn builder-sonnet to fix → re-run critic.
Repeat until all acceptance criteria are COVERED.

---

6) DOCUMENT (writer-haiku — automatic)

Spawn writer-haiku to update `.claude/CHANGELOG_AI.md` with the implementation summary.

---

7) REPORT

Present to the user:
- Acceptance criteria coverage table: [Scenario ID] | [Status] | [Test file:line]
- Files created and modified
- Migrations added (if any)
- NFR enforcement summary
- Next step: 'Run /spec-stage4-review [spec-path] to complete the AI code review gate before opening a PR.'
