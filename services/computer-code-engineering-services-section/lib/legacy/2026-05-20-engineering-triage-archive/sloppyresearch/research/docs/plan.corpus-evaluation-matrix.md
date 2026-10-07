+++
id = "plan.corpus-evaluation-matrix"
title = "Corpus Evaluation Matrix"
status = "active"
document_type = "plan"
topics = ["corpus", "evaluation"]
+++


**Purpose**: Evaluate every research paper against Proposing Relationing to determine canonical status, consolidation needs, or deletion.

**Framework**: Proposing Relationing (142KB) is THE canonical foundation. Every other paper must either:
1. Build on PR in novel/useful way → Keep & revise to cite PR
2. Restate PR ideas weirdly/outdated → Extract novel theorems, archive rest
3. Provide no novel contribution → Delete (archive to Git)

**Note**: File paths below reflect historical locations (`internal-theory/`, `txt/scientific-texts/relations/`). All canonical papers now reside under `research/papers/`; adjust references accordingly (see `research/docs/guide.directory-reorganization.md`).

---

## Evaluation Criteria

For each paper, assess:
- **Descent**: Does it reference/build on Proposing Relationing or descendants?
- **Novelty**: Does it provide theorems/insights not in PR?
- **Overlap**: How much content restates existing canonical work?
- **Quality**: Is writing clear and aligned with PR terminology?
- **Decision**: KEEP (canonical), CONSOLIDATE (extract theorems), DELETE (redundant)

---

## Internal-Theory Papers (9 documents)

### 1. proposing-a-reflexive-existence.md
- **Size**: 113KB (almost as large as PR itself!)
- **Descent**: UNKNOWN - need to check if it cites/builds on PR
- **Overlap**: Title suggests it covers similar ground to PR
- **Decision**: PENDING - likely heavy consolidation needed

Next: Compare core claims with PR; if early draft, extract unique theorems and consolidate.

---

### 2. deriving-a-reflexive-infinity-topos.md
- **Size**: 98KB (very substantial)
- **Descent**: UNKNOWN - need to verify PR lineage
- **Content**: Formalizes ∞-topos using distinction/relation framework
- **Decision**: PENDING - likely builds on PR, but verify

Next: Verify Distinction ↔ Differentiation link; keep if it extends PR into ∞-topos.

---

### 3. relational-infinity-topos-modality.md
- **Size**: 9.7KB
- **Content**: Defines RITM (already defined in PR!)
- **Descent**: PR defines RITM in line 94-96
- **Overlap**: HIGH - RITM is already in canonical foundation
- **Decision**: LIKELY CONSOLIDATE/DELETE

Next: If no novel RITM results, delete; otherwise extract and cite PR.

---

### 4. treatise-on-stratified-directed-infinity-topos-geometry.md
- **Size**: 12KB
- **Content**: Cohesive ∞-topos model, stratified geometry
- **Descent**: UNKNOWN - no PR reference found
- **Decision**: PENDING - check for novel contributions

Next: Check descent PR → deriving-* → geometry; compare with introducing-stratified-*.

---

### 5. introducing-stratified-directed-infinity-homotopy-geometry.md
- **Size**: 35KB
- **Content**: Existence as modal coherence, homotopy geometry
- **Descent**: UNKNOWN
- **Overlap**: With treatise-* (user noted "we don't have two canonical versions")
- **Decision**: CONSOLIDATE - merge with treatise-*, extract unique theorems

Next: Compare both; keep novel theorems; consolidate to a single PR‑citing paper.

---

### 6. foundations-of-relation.md
- **Size**: 35KB
- **Content**: Foundational work on relation
- **Descent**: UNKNOWN - may predate or parallel PR
- **Decision**: PENDING - check if redundant with PR's relation theory

Next: If earlier draft of PR’s relation theory, consolidate; keep only if novel results exist.

---

### 7. relational-posets.md
- **Size**: 8.8KB
- **Content**: Poset structures in relationing
- **Descent**: UNKNOWN
- **Decision**: LIKELY KEEP - specialized mathematical structure

Next: Keep if it applies PR to posets with novel results; otherwise consolidate.

---

### 8. describing-topological-dynamics-ritm.md
- **Size**: NEW (converted from .org)
- **Content**: Explicitly builds on "Relational ∞-Topos Modality" paper
- **Descent**: CITED - references RITM work
- **Decision**: CHECK REDUNDANCY - may be redundant with relational-infinity-topos-modality.md

Next: If overlapping with relational-infinity-topos-modality.md, consolidate; ensure PR lineage.

---

### 9. ritm-notes.md
- **Size**: NEW (converted from .org)
- **Content**: UNKNOWN - likely research notes
- **Decision**: PENDING

Next: If notes, move to research-notes/; if theory, evaluate against PR.

---

## txt/scientific-texts/relations/ Papers (2 documents)

### 10. composing-proposing-a-relational-existence.md
- **Size**: 8.9KB
- **Title**: "Composing Proposing a Relational Existence"
- **Descent**: Title suggests iteration/composition of PR
- **Decision**: LIKELY CONSOLIDATE - may be early draft

Next: If iteration/draft of PR, consolidate; if novel composition theory, evaluate separately.

---

### 11. proposing-a-modality-of-relationing-existence.md
- **Size**: 9.2KB
- **Content**: Modality aspect of relationing
- **Descent**: PR already covers modality
- **Decision**: PENDING

Next: If redundant with PR’s modality, consolidate; keep only if novel modal logic exists.

---

## Next Steps

1. **Read each paper systematically** - Extract main claims, check PR references
2. **Map descent lineage** - Which papers properly cite/build on PR?
3. **Identify consolidations** - Which papers need merging?
4. **Extract novel theorems** - What unique contributions exist?
5. **Execute deletions** - Remove redundant work (Git preserves history)
6. **Add citations** - Update kept papers with proper `cites_internal`, `depends_on`

---

## Related Documents
- `research/docs/map.lineage.md` - Initial thread mapping (needs major revision per this evaluation)
- `research/docs/policy.archival.md` - Supersession criteria
- `research/discipline/mathematics/relationing/category-theory/proposing-relationing/papers/proposing-relationing.md` - CANONICAL FOUNDATION
