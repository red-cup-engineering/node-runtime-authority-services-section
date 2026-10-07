+++
id = "issue.P"
title = "Refactor web bootstrap into modular API routers"
status = "open"
priority = "p2"
area = "api"
document_type = "issue"
topics = ["api", "refactor"]
created = "2025-11-10"
owner = ""
+++

Context
- `scripts/rrpr-web.py` remains a monolithic FastAPI bootstrap; `guidelines.agents.md` lists refactoring into modular `src/code/rrpi/api/` routers as an active goal.
- Core functionality already lives under `src/code/rrpi/api`, but routing, dependency injection, and metadata registration still happen in a single file, making it hard to extend.
- We need to split the bootstrap into concept-scoped routers (recognition, relation, metadata, git, etc.) and register them cleanly so the web interface stays thin.

Acceptance
- [ ] Move endpoint implementations into `src/code/rrpi/api/<concept>.py` modules with FastAPI routers.
- [ ] Update `scripts/rrpr-web.py` to only instantiate the FastAPI app, include routers, and configure middleware/logging.
- [ ] Ensure metadata decorators still work after the refactor and document the new layout in `research/docs/spec.relationing-architecture.md`.

Links
- scripts/rrpr-web.py
- src/code/rrpi/api/*
- guidelines.agents.md (Current Refactoring Status)
