+++
id = "guide.agent-hub"
title = "Agent Coordination Hub"
status = "active"
document_type = "guideline"
topics = ["agents", "coordination"]
keywords = ["hub", "workflow", "docs"]
+++

# For Agents (Codex CLI and peers)

This folder is the coordination hub for AI agents working in this repository. Favor writing to these files (and the repo in general) over long chat messages.

Contents
- `guide.agent-routine.md`: Scheduled routines (incl. every‑10‑commits checkpoint)
- `log.agent-status.md`: Latest repository stats snapshot (documents, virtual cells, edges, terms)
- `log.agent-changelog.md`: Agent‑authored checkpoints summarizing recent work
- `log.agent-todo.md`: Small, prioritized next actions
- `issues/` + `index.agent-issues.md`: Markdown issue cards and index
- `runbooks/`: Reproducible YAML runbooks when available
- `reports/`: Lint/publish manifests and related outputs
- `../dev-guides/`: Durable developer/user guides (e.g., authoring checklist)
- `ISSUE_COMPOSITION.md`: Current ordering of Issue-* cards
- `rrpr run`: Use `python -m rrp.cli.main run <runbook.yml>` (or `code/scripts/rrpr-cli.py run ...`) to execute YAML runbooks (dry-run by default, `--apply` to execute).

Ground rules
- Prefer deterministic one‑shot operations; record how to reproduce.
- Include diffs/patches and brief rationales in `log.agent-changelog.md` or linked notes.
- Keep updates concise and actionable for other agents.
- If a user message contains multiple actionable items, handle the current focus first and immediately capture the remaining items in `log.agent-todo.md` or create/update an issue under `issues/`.
- Planning/roadmap/guideline docs should include TOML frontmatter (`id`, `title`, `status`, `document_type`, `topics`, optional `notes`) so graph tooling can ingest plan metadata.
- Self-identify your tier (high/medium/low/micro) and consult the required files listed in `guidelines.agents.md` before starting work.
- Reference issue cards using Zettelkasten IDs (`Issue-A`, `Issue-B`, …) so links stay stable as the list grows.
- Whenever you edit an Issue card under `docs/for-agents/issues/`, immediately capture the change in `docs/for-agents/log.agent-changelog.md`.
- Keep graph work branch-scoped: run `python -m rrp.cli.main db switch --branch "$(git rev-parse --abbrev-ref HEAD)"` to pin your SQLite file before ingesting.
