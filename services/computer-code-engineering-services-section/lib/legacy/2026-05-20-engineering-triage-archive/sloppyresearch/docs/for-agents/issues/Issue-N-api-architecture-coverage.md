+++
id = "issue.N"
title = "Expand API architecture coverage for Relationing phases"
status = "open"
priority = "p3"
area = "api"
document_type = "issue"
topics = ["api", "relationing"]
created = "2025-11-10"
owner = ""
+++

Context
- `research/docs/spec.relationing-architecture.md` documents the concept-scoped routers and metadata decorators but lists missing coverage (git-tree mode, stabilization router, differentiation router, predicate expansion).
- The API currently exposes recognition and relation routers only; metadata coverage reports two differentiation modes.
- To keep the interface aligned with Relationing phases, we should backlog the missing routers and metadata so they can be implemented incrementally.

Acceptance
- [ ] Design and implement a `git-tree` differentiation path (router/endpoints) with `@relationing_cell` metadata.
- [ ] Add stabilization-focused endpoints (closures, reachability) with documented predicates and closure types.
- [ ] Ensure predicate coverage in metadata matches the registry in `src/code/rrpi/predicates.py`; document gaps.
- [ ] Update `research/docs/spec.relationing-architecture.md` once coverage improves, or archive the “Missing” list when the work migrates into issues/TODOs.

Links
- research/docs/spec.relationing-architecture.md
- scripts/rrpr-cli.py
- src/code/rrpi/api/*
