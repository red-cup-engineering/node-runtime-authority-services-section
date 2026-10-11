# Deletion & Consolidation Plan

**Created**: 2025-11-09  
**Status**: Ready for Execution

---

## Analysis Summary

**Critical Finding**: None of the 11 papers cite Proposing Relationing (PR). They use similar concepts (differentiation/distinction, recognition, inclusion/exclusion, RITM) but are **orphaned theory** that don't descend from the canonical foundation.

**Evidence**:
- PR is 142KB (3712 lines), status="canonical", defines all core concepts
- All other papers: status="draft", cites_internal=[], depends_on=[]
- All use PR's terminology without citing PR
- Some appear to be earlier drafts of PR itself

---

## Category 1: DELETE - Redundant with Proposing Relationing

### 1. proposing-a-reflexive-existence.md
- **Size**: 113KB (2886 lines) - almost as large as PR!
- **Status**: draft
- **Content**: Defines "Differentiate" operator, recognition, inclusion/exclusion, field of recognition
- **Overlap**: COMPLETE OVERLAP with PR - uses same concepts, same structure
- **Evidence**: Lines 32-92 define differentiation/recognition (PR lines 39-116 do the same)
- **Decision**: **DELETE** - This is an early draft of Proposing Relationing
- **Action**: Scan for any unique theorems not in PR, extract if found, then delete file

### 2. deriving-a-reflexive-infinity-topos.md  
- **Size**: 98KB (3059 lines)
- **Status**: draft
- **Alias**: "Proposing Existence" (!!!)
- **Content**: Defines "Distinction" operator (D), inclusion/exclusion, then builds ∞-topos
- **Overlap**: Foundation is redundant with PR; ∞-topos extension may be novel
- **Decision**: **CONSOLIDATE OR DELETE**
- **Action**: 
  1. Check if ∞-topos construction is novel vs PR
  2. If novel: Extract ∞-topos theorems → create new paper citing PR
  3. If redundant: Delete entirely

---

## Category 2: CONSOLIDATE - Duplicate Coverage

### 3 & 4. Stratified Geometry Papers (User explicitly noted we can't have two canonical versions)

**introducing-stratified-directed-infinity-homotopy-geometry.md**
- **Size**: 833 lines
- **Focus**: Conceptual/philosophical, existence as modal coherence, homotopy geometry
- **Content**: hlim ≃ hcolim fixed-point, constructible diagrams, Verdier duality

**treatise-on-stratified-directed-infinity-topos-geometry.md**
- **Size**: 407 lines  
- **Focus**: Technical/mathematical, cohesive ∞-topos model, stratified ∞-site axioms
- **Content**: Formal definitions, stratification functors, exit ∞-categories

**Decision**: **CONSOLIDATE INTO ONE**
- Compare both papers section-by-section
- Extract all unique theorems/definitions
- Create single "Stratified Directed ∞-Topos Geometry" paper
- **Must cite PR as foundation** + deriving-* if kept
- Delete both originals

---

## Category 3: RITM Papers - Severe Redundancy

### 5. relational-infinity-topos-modality.md
- **Size**: 310 lines (complete paper with abstract, theorems, references)
- **Content**: Full formal definition of RITM, presheaf construction, recursive realization
- **Problem**: PR already defines RITM at lines 94-96!
- **Novelty Check**: Does this add theorems beyond PR's RITM definition?
  - Yes: Formal construction, presheaf model PSh(𝒟), recursive realization theorem
- **Decision**: **CONSOLIDATE**
- **Action**:
  1. Check if PR has these formal proofs
  2. If missing: Extract theorems, add to PR or create "RITM Constructions" citing PR
  3. Delete original

### 6. describing-topological-dynamics-ritm.md
- **Size**: 95 lines
- **Content**: Explicitly builds on "Relational ∞-Topos Modality" paper (not PR!)
- **Problem**: Cites wrong foundation (should cite PR)
- **Decision**: **CONSOLIDATE OR DELETE**
- **Action**: 
  1. Merge with relational-infinity-topos-modality.md
  2. Then apply same consolidation plan as #5

---

## Category 4: NEEDS EVALUATION

### 7. foundations-of-relation.md
- **Size**: 35KB
- **Content**: Foundational work on relation
- **Status**: UNKNOWN - need to check if redundant with PR's relation theory
- **Action**: Read and compare with PR; if redundant, DELETE; if novel, revise to cite PR

### 8. relational-posets.md
- **Size**: 8.8KB
- **Content**: Poset structures in relationing
- **Action**: Check if this properly applies PR to posets; if yes, KEEP with citations; if no, DELETE

### 9. ritm-notes.md
- **Size**: Converted from .org, unknown content
- **Action**: Read; if research notes, move to research-notes/; if theory, evaluate against PR

### 10. composing-proposing-a-relational-existence.md
- **Size**: 8.9KB (txt/scientific-texts/relations/)
- **Title**: "Composing..." suggests iteration
- **Action**: Read; likely early draft of PR - if so, DELETE

### 11. proposing-a-modality-of-relationing-existence.md
- **Size**: 9.2KB (txt/scientific-texts/relations/)
- **Content**: Modality aspect
- **Action**: PR covers modality; if redundant, DELETE; if novel modal logic, extract

---

## Execution Order

1. **Quick wins - Clear deletions** (proposing-a-reflexive-existence)
2. **RITM consolidation** (3 papers → 1 or delete)
3. **Stratified geometry consolidation** (2 papers → 1)
4. **Evaluate remaining 5 papers** (foundations-of-relation, etc.)
5. **Add proper citations** to all kept papers
6. **Verify lineage** - every kept paper cites PR

---

## Success Criteria

After execution:
- ✅ Proposing Relationing is THE canonical root (unchanged)
- ✅ Every other paper explicitly cites PR in frontmatter (cites_internal or depends_on)
- ✅ No duplicate coverage (one canonical version per topic)
- ✅ All kept papers add novel contributions beyond PR
- ✅ Corpus size reduced significantly (estimate: 11 papers → 3-5 papers)

---

## Files to Update

After deletions/consolidations:
- `docs/LINEAGE_MAP.md` - Complete rewrite based on final corpus
- `docs/CORPUS_EVALUATION_MATRIX.md` - Mark decisions executed
- `scripts/audit_citations.py` - Re-run to verify all papers cite PR
- `replit.md` - Update corpus statistics
