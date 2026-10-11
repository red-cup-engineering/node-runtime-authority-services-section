+++
id = "plan.replit"
title = "RRPR Big‑Picture Guide"
status = "active"
document_type = "plan"
topics = ["infrastructure", "cms", "relationing"]
keywords = ["big-picture", "agents", "roadmap"]
++

# Relationing Research Program Repository — Big‑Picture Guide (for high‑capability agents)

This document orients a high‑capability agent (“able to do complex thinking”) to the repository’s intent, constraints, and priorities. For operational details and day‑to‑day coordination, prefer the agent hub under `docs/for-agents/`.

## Orientation
- The repository is the research. All software is thin, deterministic tooling to navigate, edit, and publish the corpus.
- Local‑first: one‑shot operations; ephemeral DB rebuilt from git + frontmatter; provenance for every operation.
- CMS‑first: focus is author → review → publish workflows with reproducible outputs (PDF, standalone HTML, Markdown bundles).

## What matters most
1. Conceptual alignment
   - Relationing semantics drive data contracts: RelCells/Edges/Provenance; predicates like `cites_internal`, `defines`, `depends_on`.
   - Differentiation modes: `frontmatter`, `git-tree`, `virtual-synthesis`.
   - Corpus integrity: consolidation decisions and lineage mapping stay synchronized with actual files under `research/papers/` and `txt/scientific-texts/`.
2. Reproducibility & determinism
   - Runbooks (THOR‑inspired) define pipelines (ingest → lint → publish).
   - Each run captures tool versions, inputs, diffs, and artifacts; publish manifests live under `docs/for-agents/reports/`.
3. Agent accessibility
   - Package as a CLI (`pip install rrpr`) with clear commands.
   - Favor editing files and committing often; treat commits as the log.
   - Coordinate via `docs/for-agents/` (routine, issues, TODOs, changelog).

## Where to look
- Plan: `research/docs/plan.cms.md` (CMS‑first software plan)
- Agent Hub: `docs/for-agents/` (routine, status, changelog, TODOs, issues, runbooks)
- Schema & Queries: `research/docs/spec.schema.md`, `research/docs/spec.query-model.md`
- Predicates: `rrpr/predicates.py`
- Foundations: `research/discipline/mathematics/relationing/category-theory/proposing-relationing/` (movements + appendices split for Proposing Relationing)

## Local Setup
- Install system dependencies (pandoc + XeLaTeX) via `make system-deps` (runs `sudo apt-get update && sudo apt-get install -y pandoc texlive-xetex`).
- Install system + Python dependencies with `make install` (wraps `system-deps` + `setup`).
- Use `make runbook ARGS="--apply"` to execute the default checkpoint runbook once dependencies are in place.
- Keep per-branch SQLite graphs isolated: `python -m rrpr.cli.main db switch --branch "$(git rev-parse --abbrev-ref HEAD)"` writes `.rrpr-active-db` and spawns `data/databases/rsc.<branch>.db`.

## Current research focus (Nov 2025)
- Canonical stack: `proposing-relationing`, `formal-axioms-of-relationing`, `constructing-relational-infinity-topoi`, `relational-infinity-topos-modality`, `stratified-directed-infinity-topos-geometry`.
- Consolidation: follow `research/docs/plan.consolidation-decisions.md` and `research/docs/policy.deletion-consolidation-plan.md` to keep only one canonical paper per topic.
- Citations & lineage: enforce `cites_internal`, `depends_on`, `builds_on`, `supersedes/superseded_by` as documented in `research/docs/guide.citation-resolution.md` and `research/docs/policy.archival.md`.

## Infrastructure priorities (immediate)
1. **Publish pipeline** (Issue-A): finalize pandoc templates, embed relational summaries (terms/citations/authors) in manifests and, eventually, PDFs/HTML.
2. **Runbook harness** (Issue-B): implement `rrpr run` so YAML runbooks (e.g., `docs/for-agents/runbooks/ten-commit-checkpoint.yml`) execute deterministically with dry-run/apply policies and artifact capture.
3. **LSP quick fixes** (Issue-C): frontmatter schema validation, repo‑wide ID rename, insert `[defines](defines)`, and citation repair inside editors.
4. **Corpus planning**: keep `research/docs/plan.cms.md`, `research/docs/plan.corpus-evaluation-matrix.md`, and `research/docs/plan.consolidation-decisions.md` aligned with actual files under `research/papers/` and `txt/scientific-texts/`.

## Big moves (pragmatic priorities)
1) Stabilize data contracts
   - Ensure `commit_hash` and predicate names are consistent across schema/code/docs.
   - Remove legacy references to `internal-theory/`; everything now lives under `research/papers/` or `txt/scientific-texts/`.
2) Reproducible pipelines
   - Implement `rrpr run` and a `publish-corpus` runbook (ingest → lint → publish PDF/HTML → manifest).
3) Edit & lint
   - LSP quick fixes for frontmatter; safe rename/add‑citation; batch linters with JSON reports.
4) Publish quality
   - Pandoc templates for PDFs/HTML; consistent typography and bibliography.
   - Include relational context (terms, citations, authors) in manifests and eventually in published outputs.

## Governance & logging
- Commit policy: make a new commit every time you change the codebase (atomic diffs, clear messages). This is the working log.
- Record high‑level checkpoints in `docs/for-agents/log.agent-changelog.md`; update `docs/for-agents/log.agent-status.md` every 10 commits.
- File issues as markdown in `docs/for-agents/issues/` and index them in `docs/for-agents/index.agent-issues.md`.

## Out‑of‑scope (for now)
- Body‑text NLP (spaCy pipelines) and long‑running services; revisit once CMS and publish pipelines are robust.

## End state
An agent can write, lint, ingest, query, and publish the corpus deterministically; another agent can reproduce the whole process from the repo with a single runbook.
