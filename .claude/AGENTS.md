# AGENTS.md — Agent Architecture & Orchestration

## Runtime Model Pins

| Agent | Model | Role | Mode |
|---|---|---|---|
| `architect-opus` | Opus | Analysis, architecture, tradeoffs | Plan (read-only) |
| `builder-sonnet` | Sonnet | Implementation, TDD, refactoring | Full access |
| `bug-fixer-sonnet` | Sonnet | Surgical bug fixes after diagnosis | Full access |
| `critic-opus` | Opus | Security/correctness review | Plan (read-only) |
| `debugger-buddy` | Sonnet | Bug diagnosis, root-cause analysis | Read + bash |
| `writer-haiku` | Haiku | Documentation, plans, summaries | Full access |
| `python-reviewer` | Haiku | Automated Python lint/type/security | Read + bash |
| `product-strategist-opus` | Opus | Product strategy, discovery, prioritization, acceptance criteria (WHAT/WHY) | Plan (read-only) |
| `qa-lead-sonnet` | Sonnet | Risk-based test strategy, coverage audit, release-readiness | Read + bash |
| `sre-devops-sonnet` | Sonnet | Terraform + GitHub Actions CI/CD, deploy automation | Full access |
| `aws-prod-debugger-opus` | Opus | Production incident diagnosis on AWS (read-only) | Read + bash |

### Role boundaries (avoid overlap)
- `product-strategist-opus` decides **WHAT/WHY** (problem, value, priority, acceptance criteria) → `architect-opus` decides **HOW** (technical design). Don't conflate.
- `qa-lead-sonnet` plans/runs/audits tests and gives the release verdict; it does **not** write test code — `builder-sonnet` owns test authoring under `.claude/rules/testing.md`. Single owner avoids dueling test policies.
- `sre-devops-sonnet` implements infra (plan-before-apply, operator applies); `aws-prod-debugger-opus` only diagnoses prod read-only and hands the fix to `sre-devops-sonnet` (infra) or `bug-fixer-sonnet` (code). `debugger-buddy` stays for app-level (non-AWS) diagnosis.

## Writing Enforcement
- Markdown artifacts (`*.md`) owned by `writer-haiku` unless human overrides.
- Provenance marker required: `<!-- written-by: writer-haiku | model: haiku -->`
- Verify: `python .claude/scripts/verify_writer_provenance.py --staged`

## Orchestration Flow

```
┌─────────────────────────────────────────┐
│            HUMAN OPERATOR               │
│        (Approve / Reject / Clarify)     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────┐
│      ARCHITECT (Opus)       │
│  RADAR analysis → plan      │
│  Parallelization guidance   │
└──────────────┬──────────────┘
               │ (approval gate)
┌──────────────▼──────────────┐
│    BUILDER(S) (Sonnet)      │
│  Parallel task groups       │
│  TDD: RED → GREEN → REFACTOR│
└──────────────┬──────────────┘
               │ (automatic)
┌──────────────▼──────────────┐
│      CRITIC (Sonnet)        │
│  Security + correctness     │
│  APPROVE / REQUEST CHANGES  │
└──────────────┬──────────────┘
               │ (if issues → fix → re-review)
┌──────────────▼──────────────┐
│      WRITER (Haiku)         │
│  Changelog + docs update    │
└──────────────┬──────────────┘
               │
            ✅ Done
```

## Pipeline Commands

| Command | Pipeline | When to Use |
|---|---|---|
| `/feature <desc>` | Architect → Approve → Builder(s) → Critic → Simplify → Writer | New features, multi-file changes |
| `/analyze <problem>` | Architect (RADAR) → Present plan | Architecture decisions, design analysis |
| `/implement <plan>` | Builder(s) parallel → Critic auto-review | Execute an existing plan |
| `/review [files]` | Critic + automated tooling | Pre-merge review |
| `/fix <bug>` | Debugger → Bug-fixer → Critic → Document | Bug investigation and fix |
| `/product <idea>` | Product-strategist (discovery → prioritize → AC) → present → Writer | Decide what/why before design; feeds /analyze + /feature |
| `/qa <scope>` | QA-lead (risk map → run → coverage audit → verdict) → Builder closes gaps | Test strategy + release-readiness gate |
| `/devops <task>` | (Architect) → SRE (implement → plan gate) → Critic → Writer (operator-log/runbook) | Terraform / GitHub Actions CI-CD changes |
| `/incident <symptom>` | AWS-debugger (read-only diagnosis) → SRE or Bug-fixer → verify → Document | Live production incident on AWS |

## Workflow Patterns

### Pattern A: New Feature (Full Pipeline)
```
/feature "Add user notifications"
  → architect-opus analyzes, produces parallelized task plan
  → user approves
  → builder-sonnet(s) implement in parallel groups
  → critic-opus auto-reviews → fix loop if needed
  → /simplify checks for unnecessary complexity
  → writer-haiku updates changelog + docs
```

### Pattern B: Bug Fix
```
/fix "Login timeout error on refresh token"
  → debugger-buddy diagnoses root cause
  → bug-fixer-sonnet writes regression test + minimal fix
  → critic-opus reviews
  → bugs.md updated
```

### Pattern C: Quick Task (Builder Only)
```
Direct request → builder-sonnet implements → critic-opus auto-reviews
```

### Pattern D: Architecture Decision
```
/analyze "Should we use Redis or PostgreSQL for session storage?"
  → architect-opus: landscape research, 3 approaches, pairwise comparison
  → recommendation with confidence level + pre-mortem
```

### Pattern E: Product Discovery → Build
```
/product "Let candidates export their evaluation as PDF"
  → product-strategist-opus: frame → discovery → prioritize (RICE) → scope slice → acceptance criteria
  → user approves
  → /analyze (architect designs HOW) → /feature (build) → /qa (verify vs the acceptance criteria)
```

### Pattern F: Quality Gate
```
/qa "branch feature/pdf-export"
  → qa-lead-sonnet: risk map → per-AC coverage (exists/missing/weak) → run suite → verdict
  → gaps → builder-sonnet writes the named load-bearing tests → re-run
  → over-testing flagged for deletion; release-readiness verdict
```

### Pattern G: Infra / CI-CD Change
```
/devops "Add SMTP-465 egress rule to the worker security group"
  → (architect-opus for blast radius if non-trivial)
  → sre-devops-sonnet: scope lock → minimal diff → validate + plan (NO apply)
  → human plan gate → critic-opus review → writer-haiku updates operator-log + deploy-runbook
  → operator runs apply + commit
```

### Pattern H: Production Incident
```
/incident "prod 503s on /evaluations since the 14:00 deploy"
  → aws-prod-debugger-opus: read-only AWS investigation → 3 hypotheses → root cause + blast radius
  → infra cause → /devops ; code cause → bug-fixer-sonnet (regression test + minimal fix)
  → operator deploys → read-only re-verify → operator-log + bugs.md entry
```

## Escalation Rules

### Builder → Architect
- Plan doesn't match reality
- Discovered requirement not in spec
- Need new dependency
- Implementation >50% larger than planned

### Critic → Human
- CRITICAL security vulnerability
- Spec violation
- Architectural deviation
- >5 warnings in single file

### Any Agent → Human
- Uncertainty about business logic
- Multiple valid approaches (no clear winner)
- Breaking change to public API
- Data migration required

## Auto-Review Policy
`critic-opus` runs automatically after EVERY implementation, whether from `/feature`, `/implement`, `/fix`, or direct builder work. No manual trigger needed. The review loops (fix → re-review) until APPROVE verdict.

## Cost Optimization
- Opus (architect + critic): analysis/planning + review — higher capability where reasoning matters
- Sonnet (builders): primary workhorse — parallel agents for independent tasks
- Haiku (writer): documentation — cheapest for text generation
- Critic reviews are shorter output than architect analysis, keeping Opus cost reasonable
- Cache architecture docs across agent spawns
- Batch critic reviews (all files at once, not per-file)
