++
id = "issue.U"
title = "Add lint/CI checks for filename ↔ id consistency"
status = "open"
priority = "p3"
area = "infra"
document_type = "issue"
topics = ["lint", "ci"]
created = "2025-11-10"
owner = ""
++

Context
- Normalization sweeps now align filenames and TOML `id` fields manually. To keep things consistent, we should add a lint script or CI check that fails when a Markdown file’s basename diverges from its `id`.
- The same tooling could ensure frontmatter exists where required and catch missing alias metadata (e.g., root `README.md`).

Acceptance
- [ ] Implement a script (Python or CLI) that scans Markdown files for frontmatter, validates the `id`, and compares it to the filename (allowing explicit `aliases` for exceptions like `README.md`).
- [ ] Wire the script into CI or a pre-commit hook so mismatches are caught automatically.
- [ ] Document the workflow (guide.agent-routine.md / dev-guides) so agents know how to run the lint locally.

Links
- docs/for-agents/guide.agent-routine.md
- manifold/docs/dev-guides/README.md
