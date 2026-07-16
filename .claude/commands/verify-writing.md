Purpose:
Verify that Markdown artifacts were authored by the writer subagent (`writer-haiku`) using provenance markers.

Inputs:
- Optional file paths from command arguments: `$ARGUMENTS`
- If no arguments are provided, verify staged Markdown files.

Steps:

1) Resolve target files
- If `$ARGUMENTS` is present, use those Markdown files.
- Otherwise use staged files from:
  - `git diff --staged --name-only`

2) Run verifier
- Command:
  - `python .claude/scripts/verify_writer_provenance.py --staged`
  - or `python .claude/scripts/verify_writer_provenance.py <file1.md> <file2.md>`

3) Report result
- `OK` means marker exists.
- `MISS` means marker missing:
  - `<!-- written-by: writer-haiku | model: haiku -->`

Output:
- Print pass/fail summary and list of files missing provenance markers.
