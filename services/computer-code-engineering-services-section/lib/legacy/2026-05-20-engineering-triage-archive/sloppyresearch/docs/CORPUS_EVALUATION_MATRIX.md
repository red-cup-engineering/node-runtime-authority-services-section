# Corpus Evaluation Matrix

**Purpose**: Evaluate every research paper against Proposing Relationing to determine canonical status, consolidation needs, or deletion.

**Framework**: Proposing Relationing (142KB) is THE canonical foundation. Every other paper must either:
1. Build on PR in novel/useful way → Keep & revise to cite PR
2. Restate PR ideas weirdly/outdated → Extract novel theorems, archive rest
3. Provide no novel contribution → Delete (archive to Git)

**Last Updated**: 2025-11-09

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

**Analysis TODO**: Compare core claims with Proposing Relationing. If this is an early draft of PR, consolidate into PR and extract any unique theorems.

---

### 2. deriving-a-reflexive-infinity-topos.md
- **Size**: 98KB (very substantial)
- **Descent**: UNKNOWN - need to verify PR lineage
- **Content**: Formalizes ∞-topos using distinction/relation framework
- **Decision**: PENDING - likely builds on PR, but verify

**Analysis TODO**: Check if "Distinction" operator connects to PR's "differentiation". If this properly extends PR's foundations into ∞-topos theory, KEEP as canonical descendant.

---

### 3. relational-infinity-topos-modality.md
- **Size**: 9.7KB
- **Content**: Defines RITM (already defined in PR!)
- **Descent**: PR defines RITM in line 94-96
- **Overlap**: HIGH - RITM is already in canonical foundation
- **Decision**: LIKELY CONSOLIDATE/DELETE

**Analysis TODO**: Check if this adds novel RITM theorems beyond PR. If not, delete. If yes, extract theorems into PR or a proper "RITM Applications" paper.

---

### 4. treatise-on-stratified-directed-infinity-topos-geometry.md
- **Size**: 12KB
- **Content**: Cohesive ∞-topos model, stratified geometry
- **Descent**: UNKNOWN - no PR reference found
- **Decision**: PENDING - check for novel contributions

**Analysis TODO**: Determine if this properly descends from PR → deriving-* → geometry, or if it's orphaned theory. Check overlap with introducing-stratified-*.

---

### 5. introducing-stratified-directed-infinity-homotopy-geometry.md
- **Size**: 35KB
- **Content**: Existence as modal coherence, homotopy geometry
- **Descent**: UNKNOWN
- **Overlap**: With treatise-* (user noted "we don't have two canonical versions")
- **Decision**: CONSOLIDATE - merge with treatise-*, extract unique theorems

**Analysis TODO**: User explicitly said we can't have two canonical stratified geometry papers. Compare both, keep novel theorems, consolidate into one paper that properly cites PR lineage.

---

### 6. foundations-of-relation.md
- **Size**: 35KB
- **Content**: Foundational work on relation
- **Descent**: UNKNOWN - may predate or parallel PR
- **Decision**: PENDING - check if redundant with PR's relation theory

**Analysis TODO**: PR already defines relation. If this is earlier draft, consolidate into PR. If it has novel relation-theoretic results, keep as specialized paper.

---

### 7. relational-posets.md
- **Size**: 8.8KB
- **Content**: Poset structures in relationing
- **Descent**: UNKNOWN
- **Decision**: LIKELY KEEP - specialized mathematical structure

**Analysis TODO**: If this properly applies PR to posets and provides novel results, keep. Otherwise consolidate.

---

### 8. describing-topological-dynamics-ritm.md
- **Size**: NEW (converted from .org)
- **Content**: Explicitly builds on "Relational ∞-Topos Modality" paper
- **Descent**: CITED - references RITM work
- **Decision**: CHECK REDUNDANCY - may be redundant with relational-infinity-topos-modality.md

**Analysis TODO**: If this and relational-infinity-topos-modality.md cover same ground, consolidate. Ensure lineage traces to PR.

---

### 9. ritm-notes.md
- **Size**: NEW (converted from .org)
- **Content**: UNKNOWN - likely research notes
- **Decision**: PENDING

**Analysis TODO**: Evaluate content. If notes/sketches, move to research-notes/. If complete theory, evaluate against PR.

---

## txt/scientific-texts/relations/ Papers (2 documents)

### 10. composing-proposing-a-relational-existence.md
- **Size**: 8.9KB
- **Title**: "Composing Proposing a Relational Existence"
- **Descent**: Title suggests iteration/composition of PR
- **Decision**: LIKELY CONSOLIDATE - may be early draft

**Analysis TODO**: User said to check if this is iteration of PR. If draft, consolidate into PR. If novel composition theory, evaluate separately.

---

### 11. proposing-a-modality-of-relationing-existence.md
- **Size**: 9.2KB
- **Content**: Modality aspect of relationing
- **Descent**: PR already covers modality
- **Decision**: PENDING

**Analysis TODO**: PR defines RITM modality. Check if this adds novel modal logic. If redundant, consolidate.

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
- `docs/LINEAGE_MAP.md` - Initial thread mapping (needs major revision per this evaluation)
- `docs/ARCHIVAL_POLICY.md` - Supersession criteria
- `txt/scientific-texts/relations/proposing-relationing.md` - CANONICAL FOUNDATION
