+++
id = "issue.O"
title = "Integrate research paper procedure into style guide and tooling"
status = "open"
priority = "p3"
area = "authoring"
document_type = "issue"
topics = ["authoring", "docs"]
created = "2025-11-10"
owner = ""
+++

Context
- `research/docs/guide.research-paper-procedure.md` defines the thesis-centered production steps but lacks frontmatter and is disconnected from `research/docs/guide.corpus-style.md` and the CLI authoring commands.
- Agents keep rediscovering the workflow because the procedure is not surfaced in `docs/for-agents/` or the templating tooling.
- We need to either fold this guidance into the corpus style guide / templates or mark it archived with clear next steps.

Acceptance
- [ ] Add TOML frontmatter to `research/docs/guide.research-paper-procedure.md` and decide whether it stays separate or merges into `research/docs/guide.corpus-style.md`.
- [ ] Update the style guide and/or templates to reference the procedure (thesis box, synthesis table, lemmas, measurement appendix).
- [ ] Ensure the CLI authoring commands (`authoring scaffold|lint`) check for these structural elements or at least link to the procedure.
- [ ] Document the integration in `docs/for-agents/log.agent-changelog.md` and close this issue once agents can find the workflow without digging.

Links
- research/docs/guide.research-paper-procedure.md
- research/docs/guide.corpus-style.md
- scripts/rrpr-cli.py
