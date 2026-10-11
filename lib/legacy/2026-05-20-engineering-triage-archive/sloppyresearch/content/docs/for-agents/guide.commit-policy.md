+++
id = "guide.commit-policy"
title = "Agent Commit Policy"
status = "active"
document_type = "guideline"
topics = ["agents", "workflow"]
keywords = ["commits", "logging"]
+++

# Commit Policy (Agents)

Principles
- Make a new commit every time you change the codebase. Keep diffs atomic and messages clear.
- Prefer small, logically isolated patches that are easy to review/revert.
- Do not commit ephemeral artifacts (venvs, build outputs, caches). Update `.gitignore` when needed.
- When a change affects behavior or policy, add a brief note to `docs/for-agents/log.agent-changelog.md`.

Message format (suggested)
- `type(scope): short summary`  
  Examples: `docs(agents): add routine and status files`, `fix(ingest): use commit_hash in selects`, `feat(cli): add publish pdf/html`.

Workflow
1) Edit files → save diffs
2) `git add -A` and `git commit -m "..."`
3) If applicable, update `docs/for-agents/log.agent-changelog.md` and `docs/for-agents/log.agent-status.md`
4) If the change is non‑trivial, add a TODO to `docs/for-agents/log.agent-todo.md` or file an issue under `docs/for-agents/issues/`
