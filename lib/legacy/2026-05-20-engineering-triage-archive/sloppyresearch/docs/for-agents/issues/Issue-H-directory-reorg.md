+++
id = "issue.H"
title = "Finalize directory reorg documentation and remove legacy references"
status = "open"
priority = "p2"
area = "docs"
document_type = "issue"
topics = ["docs", "structure"]
created = "2025-11-09"
owner = ""
+++

Context
- Directory reorg doc (`research/docs/guide.directory-reorganization.md`) has been updated but still references historical moves. Need to ensure all planning docs and ingestion scripts reference only `research/papers/` + `txt/...` paths and delete old references.

Acceptance
- [ ] Audit documentation for remaining `internal-theory/` references and update/delete accordingly
- [ ] Confirm ingestion/publish scripts only target current directories
- [ ] Update runbooks/checklists to match the new structure

Links
- research/docs/guide.directory-reorganization.md
- research/docs/report.redundancy.md
