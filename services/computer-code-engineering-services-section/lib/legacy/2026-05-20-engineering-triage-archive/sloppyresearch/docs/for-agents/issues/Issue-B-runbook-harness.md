+++
id = "issue.B"
title = "Define and implement runbook harness (`rrpr run`)"
status = "open"
priority = "p1"
area = "cms"
document_type = "issue"
topics = ["cms", "runbooks"]
created = "2025-11-09"
owner = ""
+++

Context
- We want THOR-style reproducible pipelines with dry-run/apply modes and artifact/diff capture.
- `rrpr run` command now exists (dry-run default) and executes YAML runbooks (`docs/for-agents/runbooks/*.yml`) with variable substitution. Remaining work: formalize TODO automation/log outputs, ensure publish manifests integrate with Issue-A, and add tests/docs.

Acceptance
- [ ] `rrpr run -f docs/for-agents/runbooks/ten-commit-checkpoint.yml` executes steps end-to-end (including TODO updates) with `--dry-run/--apply`.
- [ ] Policies: dry-run vs apply; auto-commit (or explicit reminder) when `policy.commit=true`.
- [ ] Reports and manifest outputs land where runbook specifies (lint JSON, publish manifest, etc.) and failures propagate non-zero exits.

Links
- docs/for-agents/runbooks/ten-commit-checkpoint.yml
- research/docs/plan.cms.md
