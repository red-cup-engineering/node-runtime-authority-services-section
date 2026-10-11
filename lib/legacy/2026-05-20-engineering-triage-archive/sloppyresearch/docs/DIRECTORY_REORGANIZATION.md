# Corpus Directory Reorganization

**Date**: 2025-11-10  
**Purpose**: Create coherent directory structure for research corpus

---

## New Structure

```
txt/scientific-texts/relations/
├── core/
│   └── proposing-relationing.md (CANONICAL ROOT)
│
├── foundations/
│   ├── formal-axioms-of-relationing.md (formal axioms, cites PR)
│   ├── foundations-of-relation.md
│   └── relational-posets.md
│
├── infinity-topoi/
│   ├── constructing-relational-infinity-topoi.md (∞-topos construction, cites PR)
│   ├── relational-infinity-topos-modality.md (RITM theory)
│   ├── describing-topological-dynamics-ritm.md (RITM dynamics)
│   └── ritm-notes.md (RITM notes)
│
├── geometry/
│   ├── introducing-stratified-directed-infinity-homotopy-geometry.md
│   └── treatise-on-stratified-directed-infinity-topos-geometry.md
│
└── explorations/
    ├── composing-proposing-a-relational-existence.md
    └── proposing-a-modality-of-relationing-existence.md
```

---

## Rationale

**core/** - The canonical root document (Proposing Relationing)

**foundations/** - Formal foundations and basic structures that build on PR:
- Formal axiomatic presentation
- Foundational relation theory
- Relational posets

**infinity-topoi/** - Higher category theory (∞-topoi, cohesive topoi, RITM):
- Cohesive ∞-topos construction
- Relational Infinity-Topos Modality (RITM) papers
- All higher-categorical constructions

**geometry/** - Stratified and directed geometry:
- Stratified directed ∞-homotopy geometry
- Directed topos geometry

**explorations/** - Papers that may not connect to core or are exploratory:
- May rely on external results
- May be unfinished explorations
- Not required to cite PR

---

## Files Moved

### From `txt/scientific-texts/relations/` → subdirectories:
- proposing-relationing.md → **core/**
- composing-proposing-a-relational-existence.md → **explorations/**
- proposing-a-modality-of-relationing-existence.md → **explorations/**

### From `internal-theory/` → `txt/scientific-texts/relations/`:
- formal-axioms-of-relationing.md → **foundations/**
- foundations-of-relation.md → **foundations/**
- relational-posets.md → **foundations/**
- constructing-relational-infinity-topoi.md → **infinity-topoi/**
- relational-infinity-topos-modality.md → **infinity-topoi/**
- describing-topological-dynamics-ritm.md → **infinity-topoi/**
- ritm-notes.md → **infinity-topoi/**
- introducing-stratified-directed-infinity-homotopy-geometry.md → **geometry/**
- treatise-on-stratified-directed-infinity-topos-geometry.md → **geometry/**

---

## Impact

- **internal-theory/** directory now contains only `lexicon.txt`
- All research papers now in disciplinary subdirectories
- Clear separation: core → foundations → applications
- Explorations directory for non-core-connected work

---

## Current Corpus State

**Total papers**: 12
- **core/**: 1 (PR - canonical root)
- **foundations/**: 3
- **infinity-topoi/**: 4
- **geometry/**: 2
- **explorations/**: 2

**Lineage established**:
- formal-axioms-of-relationing.md → cites PR
- constructing-relational-infinity-topoi.md → cites PR

**Next steps**: Continue consolidation work with organized structure
