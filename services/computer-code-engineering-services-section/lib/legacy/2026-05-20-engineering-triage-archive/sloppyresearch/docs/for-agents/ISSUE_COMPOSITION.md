++
id = "plan.issue-composition"
title = "Issue Composition (Nov 2025)"
status = "draft"
document_type = "plan"
topics = ["planning", "issues"]
keywords = ["ordering", "priorities"]
++

# Guiding Plan (Issue Composition — November 2025)

This guiding plan sequences the Issue-* cards so dependencies are satisfied and value lands in coherent waves. Use it as the default roadmap; revise when priorities or prerequisites change.

## Wave 1 — Execution Infrastructure
1. **Issue-B — Runbook harness (`rrpr run`)**  
   *Goal*: Deterministic pipelines with dry-run/apply and logging hooks.  
   *Dependencies*: none. Unlocks future waves by giving us a reliable execution shell.
2. **Issue-A — Publish pipeline (PDF + HTML)**  
   *Goal*: Canonical per-document outputs wired through the new runbook harness.  
   *Depends on*: Issue-B.
3. **Issue-J — Relational context in publish outputs**  
   *Goal*: Embed terms/citations/authors in manifests/PDF once Issue-A shipps.  
   *Depends on*: Issue-A.

## Wave 2 — Authoring & Editing Flow
4. **Issue-C — LSP quick fixes**  
   *Goal*: Repo-wide frontmatter validation + safe refactors for IDs, defines, citations.
5. **Issue-D — Frontmatter simplification / inline semantics**  
   *Goal*: Reduce required frontmatter and support inline term semantics now that Issue-C tooling exists.
6. **Issue-I — Plan/guideline frontmatter coverage**  
   *Goal*: Apply TOML to the 15 audited planning docs (list recorded in the issue).  
   *Depends on*: Issue-C (validation) + Issue-D decisions (schema simplification).

## Wave 3 — Corpus Consolidation
7. **Issue-L — Corpus evaluation matrix follow-ups**  
   *Goal*: Replace “PENDING” decisions with concrete tasks; archive `research/docs/plan.corpus-evaluation-matrix.md` once captured.
8. **Issue-M — Lineage map refresh**  
   *Goal*: Update lineage edges once Issue-L finalizes canonical statuses.  
   *Depends on*: Issue-L.
9. **Issue-H — Directory reorg documentation**  
   *Goal*: Remove legacy path references after the new lineage map lands.  
   *Depends on*: Issue-M.
10. **Issue-E — Planning-doc migration into issues**  
    *Goal*: Ensure remaining plans live as issues; tie loose ends after Issues H/L/M land.
11. **Issue-F — Checklist-to-issues** and **Issue-G — Archive redundant planning docs**  
    *Goal*: Clear residual planning debt once Issue-E is in motion.

## Wave 4 — Extended Tooling
12. **Issue-N — API architecture coverage**  
    *Goal*: Add missing routers (git-tree, stabilization) + metadata coverage after runbooks/publish stabilize.  
    *Depends on*: Wave 1 completion.
13. **Issue-O — Research paper procedure integration**  
    *Goal*: Wire the authoring checklist into templates/CLI; builds on Issue-C and Issue-D.

## Wave 5 — Platform & Docs Infrastructure
14. **Issue-P — Refactor web bootstrap into modular API routers**  
    *Goal*: Move logic into `src/code/rrpi/api/*`, keeping `scripts/rrpr-web.py` thin.  
    *Depends on*: Issue-N (router design).
15. **Issue-Q — Establish pytest testing framework**  
    *Goal*: Provide fixtures/smoke tests before large refactors/migrations.
16. **Issue-R — Set up Alembic migrations**  
    *Goal*: Controlled schema evolution once API/publish work starts adding predicates/modes.
17. **Issue-S — Implement structured logging**  
    *Goal*: JSON logs for CLI/API/runbooks feeding provenance + future observability.
18. **Issue-T — Create MkDocs documentation site**  
    *Goal*: Publish structured docs (plans, guides, schema) for researchers after consolidation.
