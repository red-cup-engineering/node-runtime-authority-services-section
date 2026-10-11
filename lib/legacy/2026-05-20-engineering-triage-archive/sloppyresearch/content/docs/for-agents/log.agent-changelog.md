+++
id = "log.agent-changelog"
title = "Agent Changelog"
status = "active"
document_type = "log"
topics = ["agents", "coordination"]
keywords = ["changelog", "history"]
+++


- Keep entries short, link to patches/diffs or notes when needed.
- Newest at top.

### 2025-11-10 0a1202a
- Summary: ten-commit checkpoint (auto)
### 2025-11-10 3718f75
- Summary: ten-commit checkpoint (auto)
### 2025-11-10 3718f75
- Summary: ten-commit checkpoint (auto)
### 2025-11-10 3718f75
- Summary: ten-commit checkpoint (auto)
### 2025-11-10 normalization-sweep
- Scope: Repository-wide normalization sweep (IDs ↔ filenames) and new infra backlog issues.
- Highlights:
  - Added TOML frontmatter + aligned filenames/IDs across `content/docs/` plans/guides; renamed files to their slugged IDs (plan.*, guide.*, map.*, spec.*).
  - Renamed agent hub assets (`guidelines.agents.md`, `replit.md`, and docs/for-agents/*.md) so filenames match `id`; updated runbooks, TODO, and references accordingly.
  - Logged normalization procedure in `guide.agent-routine.md`, expanded dev guide rules, and added issues Issue-P–Issue-T for refactors (app routers, pytest, Alembic, logging, MkDocs).
  - Recorded normalization sweep expectation under agent routines and refreshed `ISSUE_COMPOSITION.md` ordering.
  - Introduced shared Pandoc templates/CSS under `docs/publish/` and updated `rrpr publish` manifests/tooling (Issue-A groundwork).
- Follow-ups:
  - Apply normalization sweep to remaining directories (e.g., `research/papers/`) if misalignments appear.
  - Implement tooling to enforce filename/id checks during CI.

### 2025-11-10 5f49c7d
- Scope: Frontmatter normalization for repository overview, agent hub docs, and issue cards.
- Highlights:
  - Added TOML frontmatter to README.md and docs/for-agents hub files (guide.agent-hub, log.agent-todo, log.agent-status, log.agent-changelog, guide.agent-routine, guide.commit-policy, index.agent-issues).
  - Converted issue template + cards to TOML; trimmed TODO Next list to five priority items.
  - Parsed legacy planning docs (corpus evaluation matrix, lineage map, API architecture, research paper procedure) and spun out issues Issue-L–Issue-O per Issue-E.
  - Adopted Zettelkasten-style issue IDs (`Issue-A`, `Issue-B`, …), renamed all issue cards/links, and documented the new scheme in the agent hub.
  - Created `content/docs/dev-guides/` with an index plus the authoring checklist so guidance survives after issues close.
  - Recorded plan frontmatter audit results under Issue-I and drafted `ISSUE_COMPOSITION.md` to sequence Issue-* work; TODO list now mirrors that order.
  - Logged additional infrastructure issues (Issue-P–Issue-T) from `guidelines.agents.md`’s “Current Refactoring Status” so app refactor, testing, migrations, logging, and MkDocs site have dedicated cards.
  - Added initial `rrpr run` harness support (Issue-B) wired to YAML runbooks; currently supports ingest/lint/publish/status/changelog steps with dry-run default.
- Follow-ups:
  - Audit remaining planning docs for TOML coverage (Issue-I).
  - Confirm ingestion tooling parses TOML issues for graph population.

### 2025-11-10 setup-streamline
- Scope: Added Makefile targets and setup guidance for system/python dependencies.
- Highlights:
  - Introduced `Makefile` with `make setup` (venv/python deps) and `make system-deps` (pandoc + XeLaTeX).
  - Documented the workflow in `replit.md` (Local Setup) and `content/docs/dev-guides/README.md`.
- Follow-ups:
  - Run `make system-deps` locally before attempting `rrpr run --apply` or `rrpr publish --apply`.

### 2025-11-09 aaac26b
- Scope: Agent hub scaffolding; planning cleanup; big-picture guidance
- Highlights:
  - Added docs/for-agents hub (routine, status, changelog, todo, issues, runbook)
  - Updated `guidelines.agents.md` with agent routine, commit policy, in-repo issues
  - Rewrote replit.md for high-capability agents; linked plans and hubs
  - Streamlined planning docs; aligned `cites_internal` predicate in docs/code
- Follow‑ups:
  - Implement publish pipeline (Issue-A)
  - Implement runbook harness `rrpr run` (Issue-B)
  - LSP quick fixes for frontmatter (Issue-C)
- Scope: Removed standalone agent authoring checklist doc; captured guidance as Issue-K; added policy allowing deletion of archived docs.
- Highlights:
  - Created issues Issue-F–Issue-K to track migration of planning docs and authoring guidance
  - Deleted `content/docs/AGENT_AUTHORING_CHECKLIST.md` (content summarized in Issue-K / `content/relationing/research/methods/paper-authoring/relational-research-paper-specification.md`)
  - Updated `guidelines.agents.md`/docs/for-agents guidance/policy
- Follow-ups:
  - Work through issues Issue-F–Issue-J to migrate remaining planning docs and add relational publish context
