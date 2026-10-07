+++
id = "issue.S"
title = "Implement structured logging across CLI/API"
status = "open"
priority = "p3"
area = "infra"
document_type = "issue"
topics = ["logging", "infra"]
created = "2025-11-10"
owner = ""
+++

Context
- Logs are ad-hoc prints; `guidelines.agents.md` lists “Implementing structured logging” as an in-progress need.
- Deterministic operations (ingest, publish, runbooks) should emit JSON logs with timestamps, IDs, and outcomes for provenance.

Acceptance
- [ ] Choose a structured logging library/config (e.g., structlog or stdlib JSON) and add it to the runtime.
- [ ] Update CLI and FastAPI entry points to log start/end, parameters, and results for each operation.
- [ ] Document log schema and how agents can tail logs during runs.

Links
- code/scripts/rrpr-cli.py
- code/scripts/rrpr-web.py / code/rrp/api/*
- guidelines.agents.md (Current Refactoring Status)
