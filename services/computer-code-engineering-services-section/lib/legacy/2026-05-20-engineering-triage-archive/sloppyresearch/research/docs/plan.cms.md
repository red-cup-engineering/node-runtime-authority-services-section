+++
id = "plan.cms"
title = "RRPR Software Plan"
status = "active"
document_type = "plan"
topics = ["cms", "infrastructure", "publish"]
keywords = ["cli", "runbooks", "publish", "reproducibility"]
++

# RRPR Software Plan (CMS‑first, Reproducible, Agent‑Writable)

Purpose: define a pragmatic, CMS‑first software plan that makes the Relationing Research Program Repository reproducible, agent‑writable, and publishable (PDF/standalone HTML/Markdown) while keeping core ideas local‑first and deterministic.

## Scope (Now vs Later)

- In‑scope now
  - CMS workflows over Markdown+TOML frontmatter (author → review → publish)
  - Deterministic ingestion of frontmatter and git into a local SQLite graph (RelCells/Edges/Provenance)
  - Core queries for navigation (neighbors, traverse, path, closure, cycles)
  - Editing utilities that safely modify frontmatter and IDs (dry‑run → patch → commit)
  - Reproducible runbooks (THOR‑style) that pin inputs, tools, and produce artifacts + diffs
  - Packaging as a pip‑installable CLI library (agents can install and run one‑shots)
  - Publishing to: PDF, standalone HTML, Markdown bundles (per‑doc and corpus views)

- Later (explicitly out‑of‑scope now)
  - Body‑text scanning and NLP (plan: spaCy pipelines for mentions, NER, coref)
  - Rich, persistent web apps; external DB backends; multi‑user servers
  - Automatic semantic normalization beyond frontmatter

## Principles

- The repository is the research; software is thin, deterministic tooling.
- One‑shot, local‑first operations; ephemeral DB rebuilt from git + frontmatter.
- Every operation emits provenance (inputs, env, tool versions, outputs, diffs).
- Interfaces are composable; surfaces favor CLI + editor/LSP; small notebook runner optional.

## Content Model

- Document = Markdown file with TOML frontmatter (ID, title, authors, status, document_type, topics, defines, cites_internal, cites_external, depends_on, …)
- Graph = SQLite with RelCells (files/virtual), Edges (predicates), Provenance (ingestor + span + time)
- Virtual cells = deterministic IDs for terms/authors/publications

## CMS Workflows

1) Authoring
- Validate frontmatter (schema/enums), quick fixes via LSP/code actions
- Insert `[defines](defines)`, add `cites_internal` by ID with fuzzy assist
- Rename ID safely (repo‑wide refactor + backlinks update)

2) Review
- Lint corpus: missing citations/terms, invalid enums, broken IDs
- Generate diffs and reports; dry‑run patches

3) Publish
- Build per‑doc outputs: PDF (pandoc), standalone HTML (self‑contained assets), Markdown bundles (with resolved references)
- Build corpus views: terms/definitions index, citation lists, backlinks map
- Emit a reproducible manifest (hashes, tool versions)

## Reproducible Harness (Runbooks)

- Runbook YAML (THOR‑inspired)
```yaml
version: 1
name: publish-corpus
inputs:
  commit: "${GIT_COMMIT}"
  paths:
    - research/papers/*.md
policy:
  apply: false        # dry-run by default
  commit: true        # commit when apply=true
steps:
  - op: ingest
    args: {branch: "${GIT_BRANCH}", commit: "${GIT_COMMIT}"}
  - op: lint
    args: {paths: ["research/papers/*.md"]}
  - op: publish
    args: {format: [pdf, html], out_dir: dist/}
outputs:
  - artifact: dist/
  - report: reports/publish.json
```
- Harness guarantees: pin tool versions; capture env; write diffs; non‑zero exit on failure

## Interfaces

- CLI (pip‑installable `rrpr`)
  - `rrpr ingest repo|file`  → build/refresh DB from frontmatter + git
  - `rrpr query neighbors|path|closure|cycles`  → pure graph ops
  - `rrpr edit lint|rename-id|add-citation`  → safe edits (dry‑run → apply)
  - `rrpr run <runbook.yml>`  → reproducible pipeline executor
  - `rrpr publish [--format pdf,html,md] [--out dist/]`  → outputs
  - `rrpr stats`  → counts, predicates, terms

- LSP (editor integration)
  - Frontmatter schema validation and enum checks
  - Quick fixes: add/rename IDs, insert `[defines](defines)`, fix citations
  - Code actions: “Rename document ID” (repo‑wide, safe refactor)

- Notebook (optional)
  - Markdown notebook with parameterized query/edit cells and captured outputs
  - Deterministic execution (seeded), artifacts stored under `notebooks/.artifacts/`

## Publishing Outputs

- PDF: pandoc (XeLaTeX) pipeline with RRPR template and bibliography support
- Standalone HTML: pandoc self‑contained (inlined assets), consistent CSS
- Markdown bundle: resolved references + embedded metadata for portability
- Corpus indexes: terms (definitions + introduced_in), citations (internal/external), authors

## Packaging & Reproducibility

- Python package (`pip install rrpr`) with optional extras: `rrpr[publish]` for pandoc pipeline
- Lock file for CLI (uv/pip); command emits tool versions and hashes to manifest
- All ops support `--dry-run` and produce machine‑readable reports (JSON)

## Data Contracts (stabilized)

- Column names: `commit_hash` everywhere (schema/queries)
- Predicates: `cites_internal`, `cited_by`, `cites_external`, `defines`, `depends_on`, `author`, etc.
- Differentiation modes: `frontmatter`, `git-tree`, `virtual-synthesis`

## MVP (6–8 weeks)

1) Core library
- Stable schema; ingestion of frontmatter + git; predicate registry
- Queries (neighbors/path/closure/cycles); stats

2) CLI + LSP
- `rrpr ingest/query/stats`; minimal `edit lint` and `edit rename-id`
- LSP: frontmatter validation + quick fixes

3) Publish (initial)
- Per‑doc PDF + standalone HTML with shared template
- Minimal corpus indexes (terms, citations)

4) Runbooks
- `ingest+lint+publish` pipeline with dry‑run/apply; provenance manifest

## Roadmap

- Phase 1 (MVP): ingestion, queries, lint/refactor, publish pdf/html, runbooks, pip packaging
- Phase 2: edit operations (add citation by fuzzy ID, batch refactors), better corpus indexes
- Phase 3: notebook runner + graph viz cells, author contributions from git
- Phase 4: spaCy pipelines for body-text (mentions, NER, linking), RDF/SPARQL export (optional)

## Active workstreams (Nov 2025)
- Publish pipeline (Issue-A): finalize pandoc templates, stylesheet, bibliography integration, and embed relational summaries (terms/citations/authors) in manifest + output appendix.
- Runbook harness (Issue-B): implement `rrpr run` with dry-run/apply policies so YAML runbooks (checkpoint/publish) execute deterministically and capture artifacts/diffs.
- LSP quick fixes (Issue-C): frontmatter schema validation, repo-wide ID rename, insert `[defines](defines)`, add/repair `cites_internal`.
- Corpus planning: keep `research/docs/plan.consolidation-decisions.md`, `research/docs/plan.deletion-consolidation.md`, and `research/docs/plan.corpus-evaluation-matrix.md` synchronized with actual files under `research/papers/` and `txt/scientific-texts/`.

## Future enhancements
- Relational context in publish outputs (short summary of terms defined, citations made, authors) included in manifest and appended to PDFs/HTML.
- Graph-aware notebook blocks (query/viz cells) once runbook + publish pipelines are stable.
- Body-text pipelines (spaCy) to detect term mentions and citations beyond frontmatter (out-of-scope until CMS workflows mature).

## Acceptance (MVP)

- Any researcher can: write a paper (frontmatter), lint it, ingest it, run a few queries, and publish PDFs/HTML deterministically via a runbook.
- Any agent can: install the package, run a runbook in dry-run, and produce a patch + manifest for human review.

## Open Questions

- Which PDF stack (XeLaTeX vs wkhtmltopdf) best fits RRPR typography?
- How strict should lint be on `cites_internal` vs allowing unresolved references?
- What minimal LSP subset brings the most value (ID rename and citation fixes first)?
