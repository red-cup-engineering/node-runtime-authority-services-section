++
id = "guide.proposing-relationing-structure"
title = "Proposing Relationing — File Map"
status = "active"
document_type = "guide"
topics = ["relationing", "foundations"]
keywords = ["movement-map", "appendices", "orientation"]
++

# Proposing Relationing Structure

This folder contains the canonical source for the Relationing foundational treatise. Content is partitioned so agents can work on independent sections without colliding.

## Contents

- `proposing-relationing.md` — legacy single-file manuscript (kept for reference until the split is complete)
- `introduction.md` — motivation + roadmap for the five movements
- `epilogue.md` — reflective completion + future trajectories
- `movements/`
  - `movement-01-logical-origination.md`
  - `movement-02-structural-stabilization.md`
  - `movement-03-directed-dynamics.md`
  - `movement-04-geometric-cohesion.md`
  - `movement-05-emergent-containment.md`
- *(planned)* `appendix-*.md` (each appendix will become its own file)

## Workflow

1. Draft or edit within the granular files (Movement, appendix, etc.).
2. Reference files by `id` (e.g., `movement-iii-directed-dynamics`) in issues, TODOs, and publish manifests.
3. Use `python -m rrpr.cli.main publish docs ...` to render the complete treatise once the assembly order is defined in a runbook or Makefile rule.

## TODO

- Extract appendices from the monolith into sibling files (in progress).
- Define an ordered manifest (YAML/JSON) that the publish pipeline will use to stitch the parts into a single PDF/HTML bundle.
