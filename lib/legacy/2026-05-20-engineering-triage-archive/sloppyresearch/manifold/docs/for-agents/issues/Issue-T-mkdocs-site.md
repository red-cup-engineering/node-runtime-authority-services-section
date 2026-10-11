+++
id = "issue.T"
title = "Create MkDocs site for RRPR documentation"
status = "open"
priority = "p3"
area = "docs"
document_type = "issue"
topics = ["docs", "mkdocs"]
created = "2025-11-10"
owner = ""
+++

Context
- `guidelines.agents.md` notes “Creating MkDocs documentation site” as a pending task so researchers can browse plans/guides without digging through the repo.
- We now have structured frontmatter across plans/guides; surfacing them via MkDocs will make the documentation consumable.

Acceptance
- [ ] Initialize MkDocs (or Material for MkDocs) config referencing key directories (`replit.md`, `manifold/docs/dev-guides/`, `research/docs/`).
- [ ] Add navigation structure aligning with Relationing concepts (Research, Infrastructure, Agent Hub).
- [ ] Document build/preview commands and integrate with publish/runbook pipelines (dry-run is fine initially).

Links
- guidelines.agents.md (Current Refactoring Status)
- manifold/docs/dev-guides/
- research/docs/
