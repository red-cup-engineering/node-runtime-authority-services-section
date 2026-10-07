+++
id = "issue.A"
title = "Implement publish pipeline (PDF + standalone HTML)"
status = "open"
priority = "p1"
area = "publish"
document_type = "issue"
topics = ["publish"]
created = "2025-11-09"
owner = ""
+++

Context
- We need deterministic per-document outputs (PDF, standalone HTML) with consistent templates and bibliography.
- Shared Pandoc templates + CSS exist; HTML output works end-to-end. PDF builds now fail fast with a descriptive error whenever documents include invalid LaTeX (e.g., raw `\mathbf` outside math mode) so editors can fix manuscripts instead of producing broken PDFs. Remaining work: add bibliography/relational summaries and tighten document linting so such errors surface earlier.
- Shared Pandoc templates now live under `docs/publish/templates/` with a default CSS; `rrpr publish` embeds git/tool metadata in manifests. Remaining work: add bibliography integration, relational summaries, and ensure runbooks reference the new pipeline.

Acceptance
- [ ] `rrpr publish --format pdf` generates PDFs with shared template
- [ ] `rrpr publish --format html` generates self-contained HTML
- [ ] Outputs include manifest with tool versions/hashes

Links
- research/docs/plan.cms.md
