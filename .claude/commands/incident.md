Purpose:
Production incident pipeline: diagnose on AWS (read-only) → route remediation → verify → document, using aws-prod-debugger-opus. For live prod degradation/outages. Diagnosis is read-only; the operator runs any prod-mutating fix.

Input:
- `$ARGUMENTS`: The symptom — user-visible impact, error, alert, since-when, anything that changed (recent deploy, flag flip, terraform apply).

Steps:

1) Stabilize framing
- Capture observed vs expected, blast radius, and the timeline. Note recent changes: last deploy / task-def rev, flag flips, terraform applies, merges. Do NOT theorize yet.

2) Spawn aws-prod-debugger-opus
The debugger runs read-only AWS investigation: symptoms → 3 ranked hypotheses spanning app/config/infra/dependency/network → investigate highest-likelihood first, correlating CloudWatch logs + ECS service/task events + ALB target-health + RDS/Redis metrics along the request path → confirm root cause (exact resource/`file:line`/config + trigger + blast radius) → remediation handoff.
- HARD read-only: only `describe-*`/`get-*`/`list-*`/`logs`. Never `update`/`put`/`delete`/`deploy`/`apply`. Scope creds to the question (prod creds ≠ staging account `050046455645`).

3) Confirm diagnosis
- Present the root cause + evidence + blast radius + confidence. If still degrading, surface any immediate operator mitigation (scale, drain, failover, rollback to last-known-good task-def rev / image digest) — operator executes it.

4) Route remediation
- Infra / Terraform / CI-CD cause → `/devops` (sre-devops-sonnet): plan → human apply gate → verify.
- App-code cause → `bug-fixer-sonnet`: one regression test that fails on the bug → minimal fix → critic review. (Hotfix to prod follows GitFlow off `main` — auto-memory `hotfix-procedure-off-main`.)
- Architectural cause → escalate to `architect-opus`; don't ship a hack.

5) Verify resolution
- After the operator deploys the fix, re-check the same signals (logs/target-health/metrics) read-only to confirm recovery and that blast radius is closed.

6) Document
- Route to `writer-haiku`: incident entry in `infra/docs/operator-log.md`; durable root cause → `.claude/memory/bugs.md` (symptom, root cause, fix, prevention).

7) Summary
- Root cause, evidence, blast radius, remediation applied + owner, rollback used (if any), verification result, prevention follow-up.

Inter-agent handoff: diagnosis to `.claude/scratch/<task-id>/incident-diagnosis.md` (path, not contents). Agent never mutates prod.
