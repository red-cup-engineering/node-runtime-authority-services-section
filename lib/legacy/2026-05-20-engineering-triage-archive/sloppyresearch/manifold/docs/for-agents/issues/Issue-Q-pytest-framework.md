+++
id = "issue.Q"
title = "Establish pytest testing framework"
status = "open"
priority = "p2"
area = "testing"
document_type = "issue"
topics = ["testing", "infra"]
created = "2025-11-10"
owner = ""
+++

Context
- The repository lacks an active pytest suite even though `guidelines.agents.md` calls “Adding pytest testing framework” an in-progress effort.
- We need fixtures for the SQLite graph, CLI, and FastAPI layers so agents can validate changes locally before committing.

Acceptance
- [ ] Create pytest configuration (tests/ structure, conftest fixtures for temporary SQLite DB, CLI runner, FastAPI client).
- [ ] Add at least one smoke test covering ingestion/query to ensure framework runs in CI/local scripts.
- [ ] Document how to run tests in `manifold/docs/dev-guides/` or `guidelines.agents.md` and add the command to runbooks.

Links
- pytest.ini
- tests/ (currently sparse)
- guidelines.agents.md (Current Refactoring Status)
