Purpose:
Translate a requirements or design document into a layman-friendly spec document that any team member can read and understand. Produces both a .spec.md file and a shareable DOCX. Deliberately omits technical implementation details — engineers are expected to figure out the "how"; this document communicates the "what" and "why".

Follows the Spec-Driven Development Workflow (Stage 3: Spec Generation).

Input:
- `$ARGUMENTS`: One or more file paths to requirements or design documents.
  Example: /spec-requirements docs/review/my-design.md
  Example with extra context: /spec-requirements docs/review/design.md docs/extra-context.md

---

Pipeline:

1) LOAD CONTEXT

Read all documents passed in $ARGUMENTS.
Always also read:
- `project_docs/spec-driven-development-workflow.md` (workflow context — always loaded)
- `.claude/memory/active.yaml` (project state)

If $ARGUMENTS is empty, stop and ask the user: "Please provide the path to the requirements or design document you want to translate."

Identify the feature name from the document title or filename. Use it to name output files.

---

2) ANALYZE (architect-opus)

Spawn architect-opus with this task:

  "Read the provided requirements document(s) carefully. Your job is to extract and deeply understand every stated requirement — including implicit ones, forward constraints, and authorization rules. Do not propose implementation. Your output is an analysis package for a writer who will translate these into a team-readable spec.

  Produce:

  A) FEATURE SUMMARY
  One plain-English paragraph (4–6 sentences) that explains: what the system currently does or doesn't do, what problem this feature solves, and who benefits. No jargon. Write as if explaining to a smart non-engineer colleague over coffee.

  B) GLOSSARY
  Every domain-specific term, acronym, or concept a junior reader might not know. For each term: the term itself, and a 1–2 sentence plain-English explanation with a real-world analogy where possible. Include all terms that appear in the requirements.

  C) REQUIREMENT LIST
  For every distinct requirement in the document:
  - Requirement ID (REQ-001, REQ-002, …)
  - Short title (5–8 words)
  - Plain-English explanation: what is being required and why, using an everyday analogy. Explain what the current state is, what changes, and what would happen if this requirement were ignored. 2–4 sentences.
  - Business/user impact: one sentence on the real-world consequence if this is not met (for a user, admin, or the business).
  - EARS functional requirement:
      While [precondition], when [trigger], the system shall [action].
  - 2–3 BDD acceptance scenarios (Given / When / Then), each covering a distinct case (happy path, failure path, edge case).
  - Edge cases: bullet list of 1–3 non-obvious boundary conditions specific to this requirement.

  D) NON-FUNCTIONAL REQUIREMENTS
  Extract all performance, security, availability, scalability, and compliance requirements. For each:
  - NFR-ID (NFR-001, NFR-002, …)
  - Plain-English explanation (1–2 sentences, no jargon)
  - EARS format statement
  - Measurable threshold where stated (e.g. latency < 500ms)

  E) GLOBAL EDGE CASES
  Any edge cases that apply across multiple requirements (e.g. what happens if the database is unreachable, concurrent admin actions, backward compatibility constraints).

  F) OPEN QUESTIONS
  Any requirement that is ambiguous, internally contradictory, or missing a measurable threshold. Flag each with: what is unclear and what clarification is needed before implementation begins.

  Use the spec-driven-development-workflow.md as your output format guide. Return the full analysis package — do not abbreviate."

---

3) GENERATE SPEC DOCUMENT (writer-haiku)

Using the architect's analysis package, spawn writer-haiku with this task:

  "Write a spec document in Markdown. Save it to:
  project_docs/[feature-name].spec.md

  Use the spec file template from project_docs/spec-driven-development-workflow.md as your structure guide.

  STRICT RULES:
  - Write in plain English throughout. Use analogies. Avoid jargon in explanatory sections.
  - NEVER include sections titled 'What you need to build', 'Technical implementation', 'Schema', 'DDL', 'API Contract', or anything that tells engineers HOW to implement.
  - Engineers read this to understand WHAT the system must do and WHY. They decide HOW.
  - Each requirement must have: plain-English explanation, business/user impact, EARS statement, BDD scenarios, edge cases.
  - The document must be readable by a product manager, a junior engineer, and a senior engineer — and each should find it useful.
  - Include the provenance marker: <!-- written-by: writer-haiku | model: haiku -->

  DOCUMENT STRUCTURE:
  1. Cover block: feature name, date (today), status: Draft — Pending Sign-Off, prepared by: AI-assisted spec generation
  2. What is this feature? (plain-English overview, the architect's feature summary, ~300 words)
  3. Glossary (table: Term | Plain-English Meaning, all terms from the architect's glossary)
  4. Requirements — one H2 section per requirement:
     - H3: Plain-English Explanation (with analogy)
     - H3: Why It Matters (business/user impact sentence)
     - H3: Functional Requirement (EARS format, in a code block)
     - H3: Acceptance Criteria (all BDD scenarios, Given/When/Then bullet format)
     - H3: Edge Cases (bullet list)
  5. Non-Functional Requirements — one H2 section per NFR, same structure (plain English, EARS, threshold)
  6. Global Edge Cases (from the architect's analysis)
  7. Open Questions (from the architect's analysis — formatted as a numbered list with 'Owner: TBD' on each)
  8. Sign-Off Checklist:
     - [ ] Product Owner: ___________
     - [ ] Tech Lead: ___________
     - [ ] Date approved: ___________
     - [ ] Linked ClickUp task: ___________

  After writing and saving the file, report its path and line count."

---

4) GENERATE DOCX (builder-sonnet)

Spawn builder-sonnet with this task:

  "Read the markdown spec file just created at project_docs/[feature-name].spec.md.
  Write and run a Python script using python-docx to generate a DOCX version at:
  docs/review/[feature-name]-spec.docx

  Formatting rules:
  - Font: Calibri throughout. Body: 11pt. H3: 13pt. H2: 14pt. H1: 16pt.
  - Margins: 1 inch all sides.
  - Use Word styles: Title, Subtitle, Heading 1, Heading 2, Heading 3, Normal, ListBullet, ListNumber.
  - Glossary and Sign-Off rendered as tables. Header rows shaded light blue (RGB 189, 215, 238).
  - BDD scenarios rendered as indented bullet groups (Given/When/Then on separate lines, indented under scenario title).
  - EARS statements rendered in a shaded text box or bordered paragraph (light grey background).
  - Page breaks before: Glossary, Requirements section, Non-Functional Requirements, Sign-Off.
  - Footer on every page: '[Feature Name] Spec | [date] | Draft — Pending Sign-Off'
  - Cover page: Title style for feature name, Subtitle for 'Plain-English Specification', then date and status as Normal.
  - Open Questions section: numbered list with each question as a paragraph, 'Owner: TBD' on the line below each question in italics.

  After generating, print the output file path and file size in bytes.
  Clean up the temporary Python script after running it."

---

5) REPORT

Present to the user:
- Path to the markdown spec file
- Path to the DOCX file and its size
- Count of requirements and NFRs documented
- List of open questions that need answers before implementation begins (from the architect's analysis)
- Reminder: "This spec is ready for review. Share the DOCX with stakeholders. Once Product Owner and Tech Lead have signed off, the spec moves to Stage 4 (Implementation). Do not begin coding until sign-off is recorded."
