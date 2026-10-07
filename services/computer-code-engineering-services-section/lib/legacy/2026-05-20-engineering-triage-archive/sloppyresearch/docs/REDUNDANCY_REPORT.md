# Corpus Redundancy Analysis Report

Generated: 2025-11-09

## Summary

Analyzed 45 Markdown files across `txt/scientific-texts/` and `internal-theory/` directories for content redundancy.

### Duplicates Found and Removed

**2 duplicate pairs identified** (98.9% content similarity):

1. **Stability Optimization in Artificial Agents**
   - ✗ Removed: `txt/scientific-texts/intelligence/describing-stability-optimization-in-artificial-agents.md`
   - ✓ Kept: `txt/scientific-texts/intelligence/stability-optimization-in-artificial-agents.md`
   - Reason: Canonical name without verbose "describing-" prefix

2. **Proposing a Reflexive Existence**
   - ✗ Removed: `txt/scientific-texts/relations/proposing-a-reflexive-existence.md`
   - ✓ Kept: `internal-theory/proposing-a-reflexive-existence.md`
   - Reason: Foundational treatises belong in `internal-theory/` directory

### False Positives (Distinct Content)

Files with similar names but distinct content (14.3% similarity):
- `locating-stability-dynamics-in-cognitive-systems.md`
- `stability-dynamics-in-cognitive-systems.md`

These files approach the same topic from different perspectives and should both be retained.

## Thematic Groupings

Files sharing topics are not necessarily redundant - they represent different perspectives or developments of the same concepts:

### Relationing Theory (7 files)
Core theoretical development across `internal-theory/`:
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
- Thematic groupings are appropriate for an active research repository
- Multiple files on the same topic represent iterative theoretical development
- No redundant expositions found beyond the 2 duplicates

### Corpus State After Cleanup
- **43 unique Markdown files** (down from 45)
- Clean topic distribution
- Clear directory organization (`internal-theory/` for foundational work, `txt/scientific-texts/` for applied research)

## Methodology

1. **Filename analysis**: Identified files with overlapping names
2. **Content comparison**: Used difflib.SequenceMatcher for similarity ratio
3. **Metadata review**: Compared TOML frontmatter for canonical determination
4. **Thematic analysis**: Grouped files by topics from frontmatter

**Similarity thresholds**:
- >95%: Duplicate (remove one)
- 70-95%: Significant overlap (manual review)
- 30-70%: Related content (retain both)
- <30%: Distinct (retain both)
