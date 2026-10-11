+++
id = "issue.M"
title = "Refresh lineage map to reflect canonical stack and new directories"
status = "open"
priority = "p2"
area = "docs"
document_type = "issue"
topics = ["lineage", "corpus"]
created = "2025-11-10"
owner = ""
+++

Context
- `research/docs/map.lineage.md` still references `internal-theory/` paths, calls canonical decisions “pending,” and lists exploratory/applied documents without lineage edges.
- The document is meant to guide citation metadata, but it has not been updated since the directory reorg or the consolidation decisions recorded elsewhere.
- Agents need a single, current lineage view (PR → derived treatises → applications) to keep `cites_internal/depends_on` accurate.

Acceptance
- [ ] Update the lineage map with TOML frontmatter plus canonical paths under `research/papers/`.
- [ ] Reflect the six consolidation decisions: PR, formal-axioms, constructing-relational-infinity-topoi, RITM, SDIG, foundations/posets stack.
- [ ] Add applied/stability threads with explicit dependency edges (what cites PR or its descendants).
- [ ] Document remaining “review needed” items as entries in `docs/for-agents/log.agent-todo.md` or linked issues rather than inline prose.

Links
- research/docs/map.lineage.md
- docs/for-agents/issues/Issue-H-directory-reorg.md
