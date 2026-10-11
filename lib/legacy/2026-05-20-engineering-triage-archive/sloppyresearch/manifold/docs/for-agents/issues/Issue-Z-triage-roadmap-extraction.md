+++
id = "issue.Z"
title = "Extract roadmap items from pasted RSC Agent brief"
status = "open"
priority = "p2"
area = "triage"
document_type = "issue"
topics = ["roadmap", "triage"]
+++

Context
- This issue was generated from manifold/assets/Pasted--Roadmap-Relational-Source-Control-RSC-Agent-Exploration-Brief-This-document-describes-wh-1762707588300_1762707588301.txt to seed structured issue cards.

Task
- Break the pasted roadmap into atomic issues under manifold/docs/for-agents/issues/ and link each back to this source.

Source (verbatim)
```
# Roadmap: Relational Source Control (RSC) — Agent Exploration Brief

This document describes **what** to accomplish and **what constraints must hold** when turning a mixed research archive (Markdown, Python, Lean, data, etc.) into a relational source control field built directly on Git. It intentionally avoids *how* details so that the agent can choose methods.

---

## 0. Purpose & North Star

**Purpose:** Convert any Git repository of research artifacts into a runtime relational graph where:

- Only files are nodes (RelCells)
- All knowledge is edges extracted from files’ own claims (endogenous) and from Git/filesystem context (exogenous)
- Every edge carries full provenance (branch, commit, file path, content span, ingestor name, timestamp)

**Outcome:** Enable three capabilities without altering source files:
1. **Query:** ask meaningful questions across notes, code, data, and history
2. **Project:** materialize coherent subsets as branch-local worlds for drafting, experimentation, or publication
3. **Publish:** export graph/branches to web-compatible shapes (e.g., JSON-LD, RDF/SPARQL, static docs)

---

## 1. Field Model (What Must Be True)

- **RelCell:** triple `(branch, commit, path)` representing a file tracked by Git
- **Edge:** quadruple `(subject, predicate, object, provenance)`
- **Provenance:** `{ branch, commit, source_path, span, ingestor, timestamp }`
- **Endogenous edges:** declared inside files (frontmatter, imports, decorators)
- **Exogenous edges:** derived from Git and filesystem (authorship, MIME type, modification time)
- **Runtime normalization:** edges produced at read-time; never modify source files
- **Branch-local truth:** claims belong to the branch/commit where they are found
- **Open predicate set:** minimal starter vocabulary with freedom to extend

---

## 2. Intake & Staging (What to Discover)

- **Inventory:** enumerate branches and files per branch head
- **Detect exogenous context:** gather Git metadata (authorship, timestamps, renames, ancestry) and filesystem info (MIME, size, checksums)
- **Identify endogenous idioms:** frontmatter in Markdown/TOML, code-level annotations in Python/Lean
- **Define span semantics:** standardize how to indicate where a claim lives (line ranges, byte offsets, AST paths)

**Constraints:** Intake must be non-destructive, branch-aware, and repeatable at a specific commit.

---

## 3. Relation Extraction (What to Express)

- **Endogenous extraction:**
  - Markdown: `title`, `tags`, `aliases`, `cites`
  - Python: imports, decorators (`@rel(...)`)
  - Lean/other languages: imports or includes
- **Exogenous extraction:**
  - Git: authorship, commit time, ancestry, renames, tags, signatures
  - Filesystem/content: MIME type, size, checksum, path location

**Constraints:** Every edge must have provenance; no inferred or speculative relations.

---

## 4. Graph Assembly (What Store Must Provide)

- Local, file-based store (SQLite or JSON-LD)
- RelCell ID = `(branch, commit, path)`; identical files across branches remain distinct
- Updates preserve provenance; re-ingest adds new edges but never deletes history

**Goal:** Re-ingestion at the same commit must yield an identical graph.

---

## 5. Cross-Branch Unification (What Questions to Answer)

- Represent branch geometry (`forked_from`, `merges`, `derives_from`)
- Detect continuity across renames/moves without collapsing identity
- Compare divergent claims between branches

**Constraint:** No branch is privileged as "truth."

---

## 6. Query Semantics (What Queries Should Be Possible)

- **Content:** files tagged `draft` that cite a specific work
- **Code/data lineage:** what imports or derives from a given file
- **Authorship/time:** what an author changed within a time window
- **Cross-branch:** which claims differ between two branches
- **Coverage:** which files lack claims or spans

**Constraint:** Queries operate only over existing edges.

---

## 7. Projection Semantics (What a Projection Is)

- A material
```

Notes
- Truncate/segment as needed; keep each issue small and actionable.
