++
id = "guide.dev-guides"
title = "Developer & User Guides Index"
status = "active"
document_type = "guide"
topics = ["documentation", "authoring"]
keywords = ["guides", "checklists", "workflows"]
++

# Developer & User Guides

This directory holds durable guidance for people writing, editing, or operating on the Relationing Research Program Repository. When an issue produces reusable instructions (like the authoring checklist), record them here so they are discoverable after the issue closes.

## Contents
- Moved: see `content/relationing/research/methods/paper-authoring/relational-research-paper-specification.md` (from Issue-K).
- `relationing-markdown-filter.md`: Pandoc filter usage and metadata reference.
- `invariants.md`: Repository invariant paths (files that must remain at root).

## How to Contribute
1. Add TOML frontmatter with unique `id`, `title`, `status`, and `document_type = "guide"` (or `checklist`).
2. Reference the guide from relevant issues/TODOs and update this index.
3. Keep guides concise and oriented to reproducible operations.
4. Align filenames with their `id` (e.g., `guide.authoring-checklist.md` → `id = "guide.authoring-checklist"`). If platform conventions require a different filename (e.g., `README.md`), add the semantic slug under `aliases`.
5. When documenting operational runbooks, include a ready-to-run command snippet for `rrpr run <file.yml> --apply` plus any required variables.
6. For local setup, run `make install` (runs `system-deps` + `setup`) to install pandoc/XeLaTeX and the Python deps (incl. `panflute` for the Relationing filter).
