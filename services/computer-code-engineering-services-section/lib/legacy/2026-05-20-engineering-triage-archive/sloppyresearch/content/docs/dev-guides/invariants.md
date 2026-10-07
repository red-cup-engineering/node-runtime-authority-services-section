+++
id = "guide.repo-invariants"
title = "Repository Invariants"
status = "active"
document_type = "guide"
topics = ["repository", "architecture"]
keywords = ["invariants", "layout", "paths"]
+++


Files and directories that must remain at fixed locations:

| Path | Reason |
| ---- | ------ |
| `replit.md` | High-capability plan entry point referenced by multiple guides/issues; CLI tooling assumes root location. |
| `docs/for-agents/` | Coordination hub consumed by runbooks/agents. |
| `content/docs/dev-guides/` | Dev guides are indexed by ID and referenced by docs/CLIs. |
| `data/` | Canonical location for all research content by discipline. |
| `code/rrp/` | Python package root required by imports/pyproject. |
| `code/scripts/rrpr-cli.py`, `code/scripts/rrpr-web.py` | Entry points referenced by docs and Makefile. |
| `content/triage/README.md`, `content/triage/convert_docs.py` | Intake workflow for raw artifacts (referenced in docs). |
| `Makefile` | Provides `make install/setup` commands referenced in docs. |

Update this table whenever a new invariant location is introduced.
