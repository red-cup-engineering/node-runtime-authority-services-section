# Research Lineage Map for RRPR Corpus

**Purpose**: Maps iterative research threads, identifies canonical vs draft relationships, and guides citation/supersession metadata for semantic knowledge graph construction.

**Last Updated**: 2025-11-09  
**Status**: Working Document

---

## Methodology

This map was created by:
1. Scanning all 44 corpus documents for titles and content
2. Identifying thematic clusters (relationing theory, topos theory, etc.)
3. Analyzing content overlap and evolution
4. Determining canonical versions vs drafts/iterations

**Criteria for canonical status:**
- Most complete expression of ideas
- Clearest writing and organization
- Subsumes content from earlier drafts
- Marked as `foundational_treatise` or `paper` (not `note` or `draft`)

---

## Thread 1: Core Relationing Framework

**Theme**: Foundational exposition of Relationing theory - differentiation, recognition, relation, stabilization

### Documents in Thread
1. **proposing-relationing.md** ✓ CANONICAL
   - Path: `txt/scientific-texts/relations/proposing-relationing.md`
   - Title: "Proposing Relationing"
   - Status: Primary foundational treatise
   - Notes: 144KB, most comprehensive, defines core concepts

2. **proposing-a-reflexive-existence.md**
   - Path: `internal-theory/proposing-a-reflexive-existence.md`
   - Title: "Proposing a Reflexive Existence"
   - Relationship: Related but distinct perspective on existence/reflexivity
   - Status: KEEP (different focus than proposing-relationing)

3. **composing-proposing-a-relational-existence.md**
   - Path: `txt/scientific-texts/relations/composing-proposing-a-relational-existence.md`
   - Title: "Composing Proposing a Relational Existence"
   - Notes: Title suggests composition/iteration work
   - Action: REVIEW - may be draft iteration

4. **proposing-a-modality-of-relationing-existence.md**
   - Path: `txt/scientific-texts/relations/proposing-a-modality-of-relationing-existence.md`
   - Title: "Proposing a Modality of Relationing Existence"
   - Notes: Focuses on modality aspect
   - Status: KEEP (specialized perspective on modality)

### Lineage Relationships
```
proposing-relationing.md (CANONICAL)
  ↑ builds_on or supersedes?
composing-proposing-a-relational-existence.md (REVIEW NEEDED)
proposing-a-modality-of-relationing-existence.md (SPECIALIZED)
proposing-a-reflexive-existence.md (RELATED)
```

---

## Thread 2: Infinity Topos Theory

**Theme**: Mathematical formalization using ∞-topos structures, cohesive topoi, modal HoTT

### Documents in Thread

1. **deriving-a-reflexive-infinity-topos.md** ✓ CANONICAL
   - Path: `internal-theory/deriving-a-reflexive-infinity-topos.md`
   - Title: "Deriving a Reflexive Infinity Topos"
   - Status: Marked as foundational treatise, 100KB comprehensive exposition

2. **relational-infinity-topos-modality.md** ✓ CANONICAL
   - Path: `internal-theory/relational-infinity-topos-modality.md`
   - Title: "Relational Infinity Topos Modality"
   - Status: Foundational treatise on RITM (Relational ∞-Topos Modality)
   - Defines quadruple adjoint modalities: Π→ ⊣ □ᵣ ⊣ ◇ₗ ⊣ ∇←

3. **treatise-on-stratified-directed-infinity-topos-geometry.md** ✓ CANONICAL
   - Path: `internal-theory/treatise-on-stratified-directed-infinity-topos-geometry.md`
   - Title: "Treatise on Stratified Directed ∞-Topos Geometry"
   - Status: Foundational treatise (406 lines), mathematical/technical focus
   - Topics: relationing, topos-theory, geometry
   - Notes: Focuses on cohesive ∞-topos model, Kan extensions, internal HoTT

4. **introducing-stratified-directed-infinity-homotopy-geometry.md** ✓ CANONICAL
   - Path: `internal-theory/introducing-stratified-directed-infinity-homotopy-geometry.md`
   - Title: "Introducing Existential Stratified Directed Infinity-Homotopy Geometry"
   - Status: Foundational treatise (832 lines), conceptual/philosophical focus
   - Topics: relationing, homotopy-theory, topos-theory
   - Notes: Focuses on existence as modal coherence; DISTINCT from treatise (different scope/content)
   - Relationship: Parallel canonical work to treatise, not superseded

### Lineage Relationships
```
deriving-a-reflexive-infinity-topos.md (CANONICAL - foundational)
  ↓ builds_on
relational-infinity-topos-modality.md (CANONICAL - modality formalization)
  ↓ builds_on (parallel branches)
  ├─→ treatise-on-stratified-directed-infinity-topos-geometry.md (CANONICAL - technical/mathematical)
  └─→ introducing-stratified-directed-infinity-homotopy-geometry.md (CANONICAL - conceptual/philosophical)
```

---

## Thread 3: Foundations and Meta-Theory

**Theme**: Foundational work on relation, existence, posets

### Documents in Thread

1. **foundations-of-relation.md**
   - Path: `internal-theory/foundations-of-relation.md`
   - Title: "Foundations of Relation"
   - Status: 36KB, foundational work
   - Notes: May be dependency for topos work

2. **relational-posets.md**
   - Path: `internal-theory/relational-posets.md`
   - Title: "Relational Posets"
   - Topics: relationing, posets, category-theory
   - Status: Specialized mathematical structure

---

## Thread 4: Stability & Information Theory

**Theme**: Stability dynamics, information conservation, cognitive systems

### Documents Identified
- `theorem-of-information-theoretic-stability-as-reward-function.md`
- `stability-optimization-in-artificial-agents.md`
- `stability-dynamics-in-cognitive-systems.md`
- `locating-stability-dynamics-in-cognitive-systems.md`
- `principle-of-curvature-conservation.md`

**Status**: These appear to be applications of Relationing to AI/cognitive science. Need to map dependencies on core theory.

---

## Thread 5: Applied/Narrative Work

**Theme**: Media analysis, paracosms, civic texts

### Documents Identified
- Walking Dead, Phineas & Ferb, Tolstoy, Anna Karenina analyses
- Zombie ontology work
- Paracosmic models

**Status**: `intended_audience = "general"` or `"civic"`, distinct from academic papers. Should cite theoretical foundations but separate lineage.

---

## Actions Required

### Immediate (citations-1, lineage-2):
1. **Compare similar documents**:
   - ~~`introducing-stratified-*` vs `treatise-on-stratified-*` ✓ VERIFIED - both canonical, distinct content~~
   - `composing-proposing-*` vs `proposing-relationing` (iteration?)

2. **Establish dependencies**:
   - All topos theory docs should `depends_on = ["proposing-relationing"]`
   - Applied work should `cites_internal = ["proposing-relationing"]`

3. **Mark supersessions**:
   - If `introducing-*` is draft of `treatise-*`: archive with `superseded_by`

### Future (content-1):
4. **Add `builds_on` edges**:
   - `relational-infinity-topos-modality` builds_on `deriving-a-reflexive-infinity-topos`
   - `treatise-on-stratified-*` builds_on `relational-infinity-topos-modality`

5. **Add `cites_internal`**:
   - All papers citing core theory should reference `proposing-relationing`
   - Stability papers should cite `proposing-relationing` + relevant topos work

---

## Related Documents
- `docs/ARCHIVAL_POLICY.md` - Supersession criteria
- `docs/CITATION_RESOLUTION.md` - Internal citation format
- `docs/CONTROLLED_VOCABULARIES.md` - Topic/discipline standardization
