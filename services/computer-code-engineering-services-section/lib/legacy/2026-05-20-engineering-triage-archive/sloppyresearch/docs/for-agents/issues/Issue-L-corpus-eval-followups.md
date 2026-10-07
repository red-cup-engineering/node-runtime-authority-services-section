+++
id = "issue.L"
title = "Refresh corpus evaluation matrix and convert decisions into actions"
status = "open"
priority = "p2"
area = "planning"
document_type = "issue"
topics = ["corpus", "consolidation"]
created = "2025-11-10"
owner = ""
+++

Context
- `research/docs/plan.corpus-evaluation-matrix.md` still reflects legacy paths (`internal-theory/`) and open questions about the 11 flagship papers.
- Several decisions were partially covered in `plan.deletion-consolidation.md` and `plan.consolidation-decisions.md`, but the matrix has not been updated or archived.
- We need a current, machine-ingestible record of each paper's status (canonical, consolidate, delete) plus any remaining extraction work.

Acceptance
- [ ] Inventory the 11 papers listed in the matrix with their up-to-date locations under `research/papers/` or `research/notes/`.
- [ ] For each paper, record whether consolidation/deletion is complete or identify the specific extraction work that remains.
- [ ] Update or archive `research/docs/plan.corpus-evaluation-matrix.md` with TOML frontmatter and a note pointing to the new issue/tables.
- [ ] Capture any remaining per-paper tasks as entries in `docs/for-agents/log.agent-todo.md` or follow-on issues so this matrix no longer carries hidden work.

Links
- research/docs/plan.corpus-evaluation-matrix.md
- research/docs/plan.consolidation-decisions.md
