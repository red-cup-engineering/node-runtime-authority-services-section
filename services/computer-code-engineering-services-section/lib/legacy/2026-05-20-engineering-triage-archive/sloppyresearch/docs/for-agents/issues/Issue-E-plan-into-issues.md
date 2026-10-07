+++
id = "issue.E"
title = "Move redundant planning documents into structured issues"
status = "open"
priority = "p2"
area = "planning"
document_type = "issue"
topics = ["planning", "docs"]
created = "2025-11-09"
owner = ""
+++

Context
- Several planning docs (e.g., `research/docs/plan.deletion-consolidation.md`) are historical and could be slimmed down or replaced by Markdown issue cards with frontmatter.
- Goal is to reduce redundant plans, ensure active plans live as issues with TOML frontmatter, and keep `replit.md` + `plan.cms.md` as high-level guides only.
- Inventory (2025-11-10):
  - `plan.corpus-evaluation-matrix.md` → Issue-L to capture remaining consolidation work.
  - `map.lineage.md` → Issue-M to refresh lineage guidance and paths.
  - `spec.relationing-architecture.md` → Issue-N for API coverage gaps.
  - `guide.research-paper-procedure.md` → Issue-O to integrate the workflow into style guide/tooling.

Acceptance
- [ ] Inventory planning docs in `research/docs/`
- [ ] For each obsolete plan, either archive with frontmatter notes or migrate actionable items into `docs/for-agents/issues/`
- [ ] Update `guidelines.agents.md` / `replit.md` to point to issues for active workstreams

Links
- research/docs/plan.deletion-consolidation.md (archived)
- research/docs/plan.consolidation-decisions.md
- docs/for-agents/index.agent-issues.md
