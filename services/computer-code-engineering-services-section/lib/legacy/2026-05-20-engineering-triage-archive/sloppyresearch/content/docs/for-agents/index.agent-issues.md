+++
id = "index.agent-issues"
title = "In-Repo Issues Index"
status = "active"
document_type = "index"
topics = ["agents", "issues"]
keywords = ["triage", "workflow"]
+++

# In‑Repo Issues (Index & Triage)

Folder: `docs/for-agents/issues/`
- One markdown file per issue: `Issue-<zettel>-keywords.md` (Zettelkasten IDs: A..Z, AA, AB, …)
- Reference issues as `Issue-A`, `Issue-B`, … in docs/TODOs for easier cross-linking.
- Minimal frontmatter at top, followed by context and acceptance criteria.

Template
```
+++
id = "issue.AA"
title = "Short description"
status = "open"   # open | in-progress | blocked | done
priority = "p2"   # p0 | p1 | p2 | p3
area = "docs"     # ingest | query | publish | docs | infra | api | lsp | cms
document_type = "issue"
topics = ["docs"]
created = 2025-11-09
owner = ""
+++

Context
- What and why.

Acceptance
- [ ] measurable outcome 1
- [ ] measurable outcome 2

Links
- related files / commits / docs
```

Index
- Keep a short list of active issues here with links.

Active
- [Issue-A] Implement publish pipeline (PDF + standalone HTML) — docs/for-agents/issues/Issue-A-publish-pipeline.md
- [Issue-B] Define and implement runbook harness (`rrpr run`) — docs/for-agents/issues/Issue-B-runbook-harness.md
- [Issue-C] LSP quick fixes for frontmatter — docs/for-agents/issues/Issue-C-lsp-quick-fixes.md
- [Issue-D] Reduce frontmatter burden / explore inline term semantics — docs/for-agents/issues/Issue-D-frontmatter-experience.md
- [Issue-E] Move redundant planning documents into structured issues — docs/for-agents/issues/Issue-E-plan-into-issues.md
- [Issue-F] Convert Agent Authoring Checklist into priority issues — docs/for-agents/issues/Issue-F-checklist-plan-issue.md
- [Issue-G] Archive/delete redundant planning docs — docs/for-agents/issues/Issue-G-archive-old-plans.md
- [Issue-H] Finalize directory reorg documentation/refs — docs/for-agents/issues/Issue-H-directory-reorg.md
- [Issue-I] Ensure all plans/guidelines include TOML frontmatter — docs/for-agents/issues/Issue-I-plan-frontmatter.md
- [Issue-J] Add relational context to publish outputs/manifests — docs/for-agents/issues/Issue-J-publish-relational-context.md
- [Issue-K] Agent authoring guidance checklist — docs/for-agents/issues/Issue-K-agent-authoring-guidance.md
- [Issue-L] Refresh corpus evaluation matrix and convert decisions into actions — docs/for-agents/issues/Issue-L-corpus-eval-followups.md
- [Issue-M] Refresh lineage map to reflect canonical stack and new directories — docs/for-agents/issues/Issue-M-lineage-map-refresh.md
- [Issue-N] Expand API architecture coverage for Relationing phases — docs/for-agents/issues/Issue-N-api-architecture-coverage.md
- [Issue-O] Integrate research paper procedure into style guide and tooling — docs/for-agents/issues/Issue-O-research-paper-procedure.md
- [Issue-P] Refactor `code/scripts/rrpr-web.py` into modular API routers — docs/for-agents/issues/Issue-P-app-refactor.md
- [Issue-Q] Establish pytest testing framework — docs/for-agents/issues/Issue-Q-pytest-framework.md
- [Issue-R] Set up Alembic migrations for the RRPR database — docs/for-agents/issues/Issue-R-alembic-migrations.md
- [Issue-S] Implement structured logging across CLI/API — docs/for-agents/issues/Issue-S-structured-logging.md
- [Issue-T] Create MkDocs site for RRPR documentation — docs/for-agents/issues/Issue-T-mkdocs-site.md
- [Issue-U] Add lint/CI checks for filename ↔ id consistency — docs/for-agents/issues/Issue-U-id-linting.md
- [Issue-V] Integrate universal deep research refinement prompt — docs/for-agents/issues/Issue-V-deep-research-prompt.md
- [Issue-P] Refactor `code/scripts/rrpr-web.py` into modular API routers — docs/for-agents/issues/Issue-P-app-refactor.md
- [Issue-Q] Establish pytest testing framework — docs/for-agents/issues/Issue-Q-pytest-framework.md
- [Issue-R] Set up Alembic migrations for the RRPR database — docs/for-agents/issues/Issue-R-alembic-migrations.md
- [Issue-S] Implement structured logging across CLI/API — docs/for-agents/issues/Issue-S-structured-logging.md
- [Issue-T] Create MkDocs site for RRPR documentation — docs/for-agents/issues/Issue-T-mkdocs-site.md

Done
- (none yet)
