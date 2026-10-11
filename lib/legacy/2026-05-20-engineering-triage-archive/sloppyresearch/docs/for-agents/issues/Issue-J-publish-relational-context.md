+++
id = "issue.J"
title = "Add relational context to publish outputs/manifests"
status = "open"
priority = "p2"
area = "publish"
document_type = "issue"
topics = ["publish", "relcells"]
created = "2025-11-09"
owner = ""
+++

Context
- Current `rrpr publish docs` command generates PDFs/HTML and a manifest but doesn’t include relational summaries (terms defined, citations made, authors). We want relational context embedded in publishes.

Acceptance
- [ ] Extend manifest to include relational data (terms/citations/authors) per document
- [ ] Plan how to embed a relational appendix into PDFs/HTML once available
- [ ] Update `research/docs/plan.cms.md` and `replit.md` once implemented

Links
- src/code/rrpi/publish.py
- replit.md
- research/docs/plan.cms.md
