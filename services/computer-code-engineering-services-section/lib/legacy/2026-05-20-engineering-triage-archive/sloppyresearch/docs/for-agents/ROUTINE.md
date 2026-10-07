# Agent Routine

## Every 10 Commits (Checkpoint)

1) Refresh graph
- Ingest frontmatter + git to local SQLite (dry‑run if unsure)
- Record tool versions and environment used

2) Lint
- Run frontmatter/citation/term linters
- Write report under `docs/for-agents/reports/YYYYMMDD-<shortsha>-lint.json`

3) Update status
- Append current counts (documents, virtual cells, edges, terms) to `STATUS.md`

4) Changelog
- Add a short entry to `CHANGELOG.md` (scope, notable changes, follow‑ups)

5) TODOs
- Refresh `TODO.md` with 3–5 prioritized, bite‑size tasks

6) Publish (optional)
- Dry‑run publish (PDF/HTML) and include an artifacts manifest path if successful

Notes
- Keep the routine idempotent and quick; prefer dry‑run unless authorized to apply.
- When `rrpr run` is available, encode this routine as a runbook in `docs/for-agents/runbooks/`.
