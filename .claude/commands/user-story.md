Purpose:
Generate a professional, ClickUp-ready Scrum user story from a plain-language requirement. Produces a fully structured story with user journey, description, technical insights, and acceptance criteria (functional + non-functional).

Input:
- `$ARGUMENTS`: The raw requirement or feature description (one sentence to a paragraph)
- Optional context: the user may append additional context after a `---` separator — code snippets, existing docs, module names, related stories, constraints. Read and use it to produce specific Technical Insights and Dependencies rather than generic ones.

Pipeline:

1) PARSE REQUIREMENT
Read `$ARGUMENTS` and identify:
- Primary actor(s) (who benefits)
- Core capability (what they can do)
- Secondary actors (who else is affected)
- Any explicit constraints or scope exclusions mentioned

2) GENERATE STORY
Produce the full story using the structure below. Do NOT skip sections. Do NOT add sections not listed.

---

## Story Title
One line: "As a [primary actor], I want [capability] so that [benefit]."

---

## Epic
Infer the epic from the requirement domain (e.g., "Model Routing & Evaluation Intelligence", "User Management", "Billing & Subscriptions"). If ambiguous, state "TBD — assign to relevant epic."

## Labels
Comma-separated kebab-case tags reflecting the feature domain, actors, and technical area.

---

## User Journey
A top-down indented tree (use └─► arrows) showing the step-by-step flow for each actor. Cover:
- Happy path for each primary and secondary actor
- Key branch points (e.g., feature ON vs OFF, role differences)
Keep each node to one line.

---

## Description
3–5 paragraphs explaining:
1. What the feature does and why it exists
2. Any gating, precedence, or permission model
3. Trigger mechanisms (manual / automatic / both) if applicable
4. What users see in the UI when the feature is on vs off

---

## Technical Insights (High Level)
Bullet list of 5–8 implementation hints. Each bullet covers one concern:
- Data model / schema changes needed
- Service layer or business logic notes
- API surface (new endpoints or extensions)
- Cache / async / queue considerations
- UI enforcement strategy
- Integration with existing systems (reference real files/modules if context is available from the project)

Keep each bullet to 1–2 lines. Do NOT design the solution — hint at the shape.

---

## Acceptance Criteria

### Functional
Group by actor. Use GitHub-flavored checkboxes `- [ ]`. Each criterion must be:
- Testable (a QA engineer can verify it without reading code)
- Specific (names the actor, action, and expected outcome)
- Complete (covers happy path, off/disabled state, and at least one error/edge case per actor)

Cover every actor mentioned in the User Journey.

### Non-Functional
Bullet list with checkboxes covering:
- Performance / latency targets (with numbers)
- Security / authorization enforcement (both API and UI layers)
- Auditability / logging
- Resilience / queue durability (if async work is involved)
- API contract / documentation

---

## Out of Scope (This Story)
3–5 bullets of related capabilities explicitly excluded. These should be real follow-on stories, not random exclusions.

---

## Story Points Estimate
Single number using Fibonacci scale (1, 2, 3, 5, 8, 13, 21). Include a one-line justification.

## Dependencies
Bullet list of other stories, modules, migrations, or infrastructure this story depends on. Reference real system components if known from project context.

---

3) OUTPUT RULES
- Output the story as clean Markdown, ready to paste into ClickUp description field.
- Do not add a preamble ("Here is your story…"). Start directly with the Story Title section.
- Do not add a closing summary. End at Dependencies.
- Use `- [ ]` for all checklist items, never `*` or `-` alone.
- Acceptance criteria must total at least 12 items across functional + non-functional.
- If the requirement mentions an existing system feature (e.g., feature gates, model routing, evaluations), reference the real module names from project context when writing Technical Insights.
