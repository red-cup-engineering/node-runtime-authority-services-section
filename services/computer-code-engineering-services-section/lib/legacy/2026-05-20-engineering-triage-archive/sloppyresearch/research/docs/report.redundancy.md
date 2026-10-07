+++
id = "report.redundancy"
title = "Corpus Redundancy Analysis Report"
status = "active"
document_type = "report"
topics = ["corpus", "analysis"]
+++


Generated: 2025-11-09

## Summary

Analyzed 45 Markdown files across `txt/scientific-texts/` and the legacy `internal-theory/` directories for content redundancy. (All canonical files now live under `research/papers/`—see `research/docs/guide.directory-reorganization.md` for current paths.)

### Duplicates Found and Removed

**2 duplicate pairs identified** (98.9% content similarity):

1. **Stability Optimization in Artificial Agents**
   - ✗ Removed: `txt/scientific-texts/intelligence/describing-stability-optimization-in-artificial-agents.md`
   - ✓ Kept: `txt/scientific-texts/intelligence/stability-optimization-in-artificial-agents.md`
   - Reason: Canonical name without verbose "describing-" prefix

2. **Proposing a Reflexive Existence**
   - ✗ Removed: `txt/scientific-texts/relations/proposing-a-reflexive-existence.md`
   - ✓ Kept: (now `research/discipline/mathematics/relationing/category-theory/formal-axioms-of-relationing/papers/formal-axioms-of-relationing.md`)
   - Reason: Foundational treatises belong in the canonical stack (`research/papers/`)

### False Positives (Distinct Content)

Files with similar names but distinct content (14.3% similarity):
- `locating-stability-dynamics-in-cognitive-systems.md`
- `stability-dynamics-in-cognitive-systems.md`

These files approach the same topic from different perspectives and should both be retained.

## Thematic Groupings

Files sharing topics are not necessarily redundant - they represent different perspectives or developments of the same concepts:

### Relationing Theory (7 files)
Core theoretical development (now under `research/papers/`):
- `deriving-a-reflexive-infinity-topos.md`
- `foundations-of-relation.md`
- `proposing-a-reflexive-existence.md`
- `relational-infinity-topos-modality.md`
- `relational-posets.md`
- `introducing-stratified-directed-infinity-homotopy-geometry.md`
- `treatise-on-stratified-directed-infinity-topos-geometry.md`

### Topos Theory (4 files)
Mathematical formalization:
- `deriving-a-reflexive-infinity-topos.md`
- `introducing-stratified-directed-infinity-homotopy-geometry.md`
- `relational-infinity-topos-modality.md`
- `treatise-on-stratified-directed-infinity-topos-geometry.md`

### Category Theory (3 files)
- `deriving-a-reflexive-infinity-topos.md`
- `foundations-of-relation.md`
- `relational-posets.md`

## Recommendations

### Completed Actions
✅ Removed 2 duplicate files (git tracked, recoverable if needed)  
✅ Retained canonical versions based on naming conventions and directory structure

### No Further Action Required
- Thematic groupings indicate iterative theoretical development rather than duplication.

### Corpus State After Cleanup
- **43 unique Markdown files** (down from 45)
- Clean topic distribution
- Clear directory organization (`research/papers/` for canonical work, `txt/scientific-texts/` for historical drafts)

## Methodology (brief)

- Filename, content, and frontmatter comparison with thematic grouping.
