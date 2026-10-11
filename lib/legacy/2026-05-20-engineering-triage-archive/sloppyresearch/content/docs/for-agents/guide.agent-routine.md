+++
id = "guide.agent-routine"
title = "Agent Routine"
status = "active"
document_type = "guideline"
topics = ["agents", "routine"]
keywords = ["checkpoint", "runbook"]
+++


## Every 10 Commits (Checkpoint)

1) Refresh graph
- Ingest frontmatter + git to local SQLite (dry-run if unsure)
- Record tool versions and environment used
- Before ingesting, run `python -m rrp.cli.main db switch --branch "$(git rev-parse --abbrev-ref HEAD)"` so the branch has its own `rsc.<branch>.db`.

2) Lint
- Run frontmatter/citation/term linters
- Write report under `docs/for-agents/reports/YYYYMMDD-<shortsha>-lint.json`

3) Update status
- Append current counts (documents, virtual cells, edges, terms) to `docs/for-agents/log.agent-status.md`

4) Changelog
- Add a short entry to `docs/for-agents/log.agent-changelog.md` (scope, notable changes, follow‑ups)

5) TODOs
- Refresh `docs/for-agents/log.agent-todo.md` with 3–5 prioritized, bite‑size tasks

6) Publish (optional)
- Dry‑run publish (PDF/HTML) and include an artifacts manifest path if successful

Notes
- Keep the routine idempotent and quick; prefer dry-run unless authorized to apply.
- Run `python -m rrp.cli.main run docs/for-agents/runbooks/ten-commit-checkpoint.yml --apply` (or `code/scripts/rrpr-cli.py run ...`) once the harness is ready for full execution.
- When `rrpr run` is available, encode this routine as a runbook in `docs/for-agents/runbooks/`.

## Normalization Sweeps (Frequent / On Request)

**Definition**: A normalization sweep aligns filenames, IDs, and references with canonical content. It includes:
- Auditing Markdown/TOML frontmatter for `id`, `title`, `status`, and ensuring filenames match `id`.
- Verifying cross-references (`cites_internal`, issue links, README references) use the same IDs.
- Documenting any renames/moves in `docs/for-agents/log.agent-changelog.md` and updating affected issues/TODOs/runbooks.

**Frequency**:
- Run at least once per 10-commit checkpoint (can bundle with the routine above).
- Run immediately when a user requests consistency checks or after large refactors (directory moves, new ID schemes).

**Workflow**:
1. Inventory targets (e.g., `rg` for malformed IDs, list of recently touched docs).
2. Apply consistent renames (filenames + frontmatter + references) using deterministic scripts.
3. Record results in `docs/for-agents/log.agent-changelog.md` and create/update issues if follow-up work remains.
