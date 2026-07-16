<!-- written-by: writer-haiku | model: haiku -->
Purpose:
AI-assisted requirements clarification for Stage 1 of the spec-driven development workflow.
Takes raw stakeholder notes or a meeting transcript and produces a structured requirements document
ready for Product Owner sign-off.

Follows Stage 1 of project_docs/spec-driven-development-workflow.md.

Input:
- `$ARGUMENTS`: Path to raw stakeholder notes, a meeting transcript, or an inline description.
  Example: /spec-stage1 project_docs/raw-stakeholder-notes.md
  Example: /spec-stage1 "Customers need to export their audit logs to CSV"

---

Pipeline:

1) LOAD CONTEXT

Read:
- All files passed in $ARGUMENTS
- `project_docs/spec-driven-development-workflow.md` (Stage 1 guidance)
- `.claude/memory/active.yaml` (project state)

If $ARGUMENTS is empty, stop and tell the user:
"Please paste your raw stakeholder notes or provide a file path. Example: /spec-stage1 docs/meeting-notes.md"

Identify the feature name from the document or description. Use it to name output files.

---

2) ANALYZE (architect-opus)

Spawn architect-opus with this task:

  "Read the provided stakeholder notes carefully. Your job is to structure and clarify — not to design solutions.

  Produce:

  A) PROBLEM RESTATEMENT
  A 2–3 sentence problem statement in the team's own words.
  Format: 'Currently, [state of the world]. This causes [pain]. We need [capability] so that [business outcome].'
  Focus on the problem, not any solution.

  B) STRUCTURED USER STORIES
  For every distinct user need in the notes, write a user story:
  - Format: 'As a [role], I need [capability] so that [business value].'
  - Do not propose solutions. Describe needs only.
  - If a role is unstated, infer from context or mark [role: TBD].
  - Include at least one story per distinct stakeholder mentioned.

  C) CONSTRAINTS
  List all constraints explicitly stated or implied:
  - Performance (latency targets, throughput)
  - Security or compliance (SOC 2, GDPR, audit trail requirements)
  - Budget or timeline
  - Technical constraints ('cannot change the existing API')

  D) CLARIFYING QUESTIONS
  For every ambiguity or unstated assumption, write a specific question.
  Format: 'Q: [The specific question]. Context: [Why this matters — what decision depends on this answer].'
  Mark each: [BLOCKING] (must resolve before Stage 2 begins) or [NON-BLOCKING].

  E) ASSUMED NEEDS
  Requirements likely needed but not mentioned. Mark each [ASSUMED NEEDED] with one sentence explaining why.
  Do not add scope — surface risks for the PO to confirm or deny.

  Return all five sections. Read Stage 1 of spec-driven-development-workflow.md for guidance."

---

3) GENERATE REQUIREMENTS DOCUMENT (writer-haiku)

Using the architect's analysis, spawn writer-haiku:

  "Write a requirements document and save it to:
  project_docs/requirements/[feature-name]-requirements.md

  Structure:
  1. Header: Feature name, date (today), Status: Draft — Awaiting PO Sign-Off
  2. Problem Statement (from architect)
  3. Stakeholder (who requested this)
  4. User Stories (structured list from architect)
  5. Constraints (from architect)
  6. Open Questions — blocking first, then non-blocking (from architect)
  7. Assumed Needs (from architect)
  8. Sign-Off block:
       - [ ] Product Owner confirmed: ___________
       - [ ] Date confirmed: ___________
       - [ ] ClickUp task linked: ___________

  Include provenance marker on line 1: <!-- written-by: writer-haiku | model: haiku -->
  Report the file path and line count after writing."

---

4) REPORT

Present to the user:
- Path to the requirements document
- Count of user stories
- List of BLOCKING questions to resolve with stakeholders before Stage 2
- Reminder: 'Get Product Owner sign-off on this document before Stage 2 (Human Design). Stage 2 is human-only — no AI involvement.'
