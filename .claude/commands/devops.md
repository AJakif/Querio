Purpose:
Infra / CI-CD change pipeline: plan → implement Terraform or GitHub Actions safely → validate (plan, no apply) → review → document, using sre-devops-sonnet. Plan-before-apply, never destructive by default; the operator runs apply + commit.

Input:
- `$ARGUMENTS`: The infra/CI-CD task (Terraform resource/module, workflow change, deploy automation, secret wiring, observability, rollback).

Steps:

1) Load canonical context
- `infra/docs/devops-handbook.md` (authoritative how-to; `ci-cd-handover.md` is stale), `infra/docs/operator-log.md` (pending/scheduled state), `infra/docs/deploy-runbook.md`.
- The specific `.tf`/workflow being changed + the module it depends on. For non-trivial design, spawn `architect-opus` first to weigh blast radius and rollback.

2) Spawn sre-devops-sonnet
The SRE runs: scope lock (resources touched, what's NOT touched, rollback) → minimal-diff implement (follow existing module/workflow patterns, version-pin, parameterize via SSM/vars) → verify (`terraform validate` + `fmt -check <files>` + `plan`; workflows: concurrency groups distinct, secret refs resolve). Reports each check RAN/SKIPPED/FAILED.
- Honors repo traps: `fmt -check` on specific files (never `-recursive`), absolute `terraform.exe` path, explicit `--task-definition <rev>` on ECS redeploy, SHA-pinned `APP_IMAGE`, `-T </dev/null` in ssh heredocs, Windows cp1252 JSON reads, single alembic head after merges.

3) Plan gate (HARD)
- Present the `terraform plan` (or precise summary) and STOP for human go-ahead before any `apply` on shared/staging/prod state. Default is read-only. Any destructive/replace/force-unlock op gets an explicit callout + rollback before proceeding. Do not modify prod migrations or main-branch deploy workflows without explicit approval.

4) Review (critic-opus)
- Spawn `critic-opus` on the diff. Infra/migration/config/flag changes are OPS-ACTION-REQUIRED-relevant — critic emits the flag; ensure a matching `deploy-runbook.md` entry results.

5) Document
- Route to `writer-haiku`: append the pending/manual action to `infra/docs/operator-log.md` and any deploy-time step to `infra/docs/deploy-runbook.md` (structured entry, `RB-id`). Provenance marker on docs.

6) Summary
- Resources/workflows changed, validation results, the plan diff summary, rollback path, the operator-log/runbook entries, and the explicit "operator to run apply + commit" next step.

Inter-agent handoff: artifacts to `.claude/scratch/<task-id>/<phase>.md` (paths, not contents), COMPACT mode. Agent never applies or commits.
