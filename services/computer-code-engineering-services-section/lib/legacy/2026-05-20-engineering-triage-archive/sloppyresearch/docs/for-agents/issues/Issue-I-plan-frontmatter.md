+++
id = "issue.I"
title = "Ensure all plans/guidelines include TOML frontmatter"
status = "open"
priority = "p3"
area = "planning"
document_type = "issue"
topics = ["planning", "frontmatter"]
created = "2025-11-09"
owner = ""
+++

Context
- We’ve started adding TOML frontmatter to plans (`replit.md`, `plan.cms.md`, `plan.deletion-consolidation.md`). Need to audit remaining planning documents and add frontmatter so ingestion tools can treat them as first-class RelCells.
- Audit (2025-11-10): Missing `+++` blocks detected (now resolved) in
  - `research/docs/policy.archival.md`
  - `research/docs/guide.citation-resolution.md`
  - `research/docs/plan.consolidation-decisions.md`
  - `research/docs/guide.controlled-vocabularies.md`
  - `research/docs/plan.corpus-evaluation-matrix.md`
  - `research/docs/guide.corpus-style.md`
  - `research/docs/guide.directory-reorganization.md`
  - `research/docs/map.lineage.md`
  - `research/docs/analysis.pr-vs-drafts.md`
  - `research/docs/spec.query-model.md`
  - `research/docs/report.redundancy.md`
  - `research/docs/spec.relationing-architecture.md`
  - `research/docs/guide.research-paper-procedure.md`
  - `research/docs/spec.schema.md`
  - `research/docs/analysis.theorem-comparison.md`

Acceptance
- [ ] Audit `research/docs/*.md` for planning/guideline docs lacking frontmatter
- [ ] Add TOML frontmatter (id/title/status/document_type/topics) where missing
- [ ] Document the policy in `guidelines.agents.md` (done) and mark this issue complete

Links
- guidelines.agents.md (policy)
- research/docs directory
