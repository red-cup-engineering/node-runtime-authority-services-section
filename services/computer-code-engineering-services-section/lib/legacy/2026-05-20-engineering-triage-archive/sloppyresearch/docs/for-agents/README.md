# For Agents (Codex CLI and peers)

This folder is the coordination hub for AI agents working in this repository. Favor writing to these files (and the repo in general) over long chat messages.

Contents
- `ROUTINE.md`: Scheduled routines (incl. every‑10‑commits checkpoint)
- `STATUS.md`: Latest repository stats snapshot (documents, virtual cells, edges, terms)
- `CHANGELOG.md`: Agent‑authored checkpoints summarizing recent work
- `TODO.md`: Small, prioritized next actions
- `runbooks/`: Reproducible YAML runbooks when available

Ground rules
- Prefer deterministic one‑shot operations; record how to reproduce.
- Include diffs/patches and brief rationales in `CHANGELOG.md` or linked notes.
- Keep updates concise and actionable for other agents.
