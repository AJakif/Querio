# Testing Rules

## Scope
Applies when editing `tests/**` or when any agent (builder-sonnet, bug-fixer-sonnet, critic-opus, debugger-buddy) is authoring or reviewing tests.

This file is the **canonical source** for test-value policy in this project. Agent prompts reference it — do not duplicate the content into agent prompts, point at this file instead.

## Core Principle: Load-Bearing Tests Only

Every test must earn its place. A test earns its place only if it would **fail when the feature is broken in a way that causes visible pain**. Tests that do not meet that bar are noise — they cost time to write, run, and maintain while catching nothing, and they obscure the real tests in the diff.

Guiding aphorisms:
- "Write tests. Not too many. Mostly integration." (Guillermo Rauch, popularized by Kent C. Dodds)
- Kent Beck's test desiderata: tests should be *predictive* (fails when the code is broken), *inspiring* (when it fails, you know what to do), *specific* (one reason to fail), and *writable* (cost proportional to value).
- Test behavior, not implementation. If refactoring the internals breaks the test, the test was testing the wrong thing.

## The Load-Bearing Filter

Before writing any test, answer **yes to all four**. If you cannot, do not write the test:

1. **Failure signal** — If a realistic bug were introduced in the code under test, would *this specific test* fail?
2. **User-visible consequence** — If the asserted behavior were broken in production, would a user, operator, or downstream service notice?
3. **Non-redundant** — Is there no other test in the suite that would already catch the same bug?
4. **Not testing the framework** — Am I testing my code, or am I testing Pydantic / SQLAlchemy / FastAPI / the standard library?

Proposed tests that fail any question get dropped, not weakened.

## Ban List — Do Not Write These

These categories are AI-common and net-negative:

- **Getter/setter echoes** — `assert user.name == "test"` after `user = User(name="test")`
- **Framework behavior** — `assert isinstance(response, JSONResponse)`, `assert request.method == "POST"`, `assert response.status_code == 200` with no assertion about the body
- **Pydantic validation theatre** — testing that an `int` field rejects a string; Pydantic already does that and you don't need to re-test it
- **Type-system duplication** — `assert isinstance(x, str)` when the signature already promises `str`
- **Mock-was-called-ism** — `assert mock.called` or `mock.assert_called_once()` with no assertion about *what the code did with the result*
- **Parametrize explosions** — 20 parameter rows when 2–3 representatives cover the equivalence classes
- **Defensive-by-accident** — asserting that passing `None` where the signature says `str` raises `TypeError`; the type system prevents this at the caller
- **Happy-path duplication** — three near-identical create-flow tests with minor input variation
- **Format trivia** — timestamp rounding, UUID format, hash length — unless the spec explicitly mentions them
- **Tautologies** — `assert obj.x + obj.y == obj.total` where `total` is literally defined as `x + y`
- **Over-mocked unit tests that pass when the real system is broken** — if every collaborator is mocked, the test is verifying your mocks, not your code

## Test Budget

Targets and ceilings by change type:

| Change type | Target | Ceiling | Strictness |
|---|---|---|---|
| Single-function bug fix | Exactly 1 regression test | 1 | **Hard** — no siblings, no parametrize variants |
| New endpoint (no new logic) | 1 happy + 1 auth/authz + 1 validation-boundary | ≤5 | Soft |
| New service method | 1 happy + 1 failure + 1 per *distinct* branch | ≤5 | Soft |
| New feature (multi-file) | 3–7 tests total | ≤10 | Soft |
| Refactor with existing coverage | 0 new tests | 0 | **Hard** — refactors do not add tests |

Exceeding a **soft** ceiling: emit a one-line `JUSTIFIED: +N tests because [concrete risk tied to a specific failure mode]` in your summary. No justification → cut the extras.

Exceeding a **hard** ceiling: do not do it. Escalate instead. If you believe a bug fix needs more than one regression test, the bug is actually two bugs — file them separately and run two `/fix` cycles.

## The Delete-First Drill

Before finalizing tests, re-read your test file test-by-test and ask: *"If I deleted this test and ran the suite against a broken version of my implementation, which tests would still fire and which would still pass?"*

Any test that would **not** fire on a realistic break gets deleted.

## Prefer Integration Over Unit When Possible

A single integration test that exercises real collaborators often replaces ten over-mocked unit tests and catches more real bugs. When in doubt, climb the pyramid: push tests up toward the contract that callers actually use. Solitary (fully-mocked) unit tests are a last resort for isolating non-deterministic or slow code.

The test pyramid is a guideline, not a mandate. A fatter middle (integration tests) is fine when the integration surface is the source of real bugs.

## Scope Rule: New Tests Only

This policy governs tests **you are about to write**. Do not retroactively delete existing tests as a side effect of touching adjacent code. Cleanup of pre-existing trivial tests is a separate, intentional task — mixing it into feature work creates scary diffs and obscures the real change.

If you notice an existing test that clearly violates this policy while touching adjacent code, flag it as `FOLLOW-UP:` in your summary. Do not delete it in the same change.

## Fixture Rules

- **Deterministic** — no `time.time()`, no unseeded `random`, no real network, no real clock
- **Isolated** — no test ordering dependencies, no shared mutable state between tests
- **Meaningful assertions only** — `assert result is not None` is a placeholder, not an assertion

## Output Expectations

- Report what was tested and what was not.
- Call out residual risk when tests cannot be run.
- If you hit a soft budget ceiling, state the `JUSTIFIED: +N` line in your summary.
- If you considered a test and dropped it because it failed the Load-Bearing Filter, no need to report it — silent drops are fine.
