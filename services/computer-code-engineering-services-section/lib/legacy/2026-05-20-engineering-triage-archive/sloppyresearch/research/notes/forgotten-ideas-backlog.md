+++
# ===== IDENTITY =====
id = "forgotten-ideas-backlog"
title = "Forgotten Ideas & Future Work Backlog"
aliases = []

# ===== AUTHORIAL =====
authors = ["emsenn"]
date_created = "2025-11-09"
date_modified = "2025-11-09"
status = "working"

# ===== CLASSIFICATION =====
document_type = "note"
topics = ["meta", "planning", "backlog"]
disciplines = []

# ===== CITATIONS - INTERNAL =====
cites_internal = []
cited_by_internal = []

# ===== RELATIONAL METADATA =====
depends_on = []

# ===== PUBLICATION =====
published = false
+++


**Purpose**: This document collects incomplete ideas, future work sections, architectural TODOs, and planned enhancements extracted from the corpus and conversation history.

**Last Updated**: 2025-11-09  
**Status**: Living document - add new ideas as they emerge

---

## Provenance Summary

**Sources**: This backlog was compiled from:
1. **Conversation History** (Nov 2025): Initial cleanup goals, math notation standardization, redundancy detection
2. **plan.replit.md** "Potential Future" section: RDF/SPARQL, D3.js, Cytoscape.js, Alembic, Jinja2
- 3. **research/docs/spec.relationing-architecture.md** "Missing (Future Work)": git-tree endpoints, Stabilization/Differentiation routers
4. **Corpus "Future Work" sections**: Theoretical papers proposing extensions
5. **Active bugs**: Stats CLI term display issue (conversation Nov 2025)
6. **Writing project TODOs**: Fictional memoir & zombie novel 30-day structures

**Conversation-Derived Items** (explicitly mentioned in session):
- Math notation standardization (started, 195/1,118 converted)
- Redundancy detection & consolidation (completed, 2 duplicates removed)
- Stats CLI bug (terms show 0 despite DB correctness)
- Extract forgotten ideas (this document)

---

## Infrastructure & Tooling

### API Architecture (High Priority)
- [ ] **git-tree mode endpoints**: Add endpoints for querying git-tree differentiated cells
- [ ] **Stabilization router**: Implement closure operations, fixed points, transitive closures aligned with Relationing theory
- [ ] **Differentiation router**: Create explicit differentiation operations endpoint
- [ ] **Expand predicates**: Add more relation types beyond current 45+ (see `rrpr/predicates.py`)

### Database & Storage
- [ ] **RDF/SPARQL export**: Enable export of knowledge graph to RDF format for semantic web compatibility
- [ ] **Alembic migrations**: Add database migration support for schema evolution
- [ ] **Stats CLI bug**: Fix term count display showing 0 despite correct database rows (non-blocking)

### Visualization
- [ ] **D3.js graph viz**: Interactive knowledge graph visualization in web interface
- [ ] **Cytoscape.js**: Alternative network graph library for complex topologies
- [ ] **Cell relationship viewer**: Visual explorer for RelCell connections and provenance

### Web Interface
- [ ] **Jinja2 templating**: Replace inline HTML with proper template system
- [ ] **Search interface**: Full-text search across corpus from web UI
- [ ] **Citation graph**: Visual display of internal citation network
- [ ] **Commit timeline**: Git history visualization showing corpus evolution

---

## Theoretical Work

### From "Proposing a Reflexive Existence"
Appendix F outlines open mathematical formalizations:
- [ ] **Cubical type theory formalization**: Encode reflexive existence in Cubical Agda or Lean
- [ ] **Homotopy coherence**: Formal proof of stability conditions in higher category theory
- [ ] **Synthetic differential geometry**: Express reflexive dynamics using SDG
- [ ] **Topos-theoretic semantics**: Complete categorical semantics for RITM

### From "Relational Infinity-Topos Modality"
- [ ] **Cubical Agda implementation**: Formalize RITM in proof assistant
- [ ] **Extensions to physics**: Apply RITM to gauge theories and general relativity
- [ ] **Computational realizability**: Implement RITM operations as algorithms

### From "Reflexive Calibration Theory"
- [ ] **Partial calibration formalization**: Complete math for $0 < g < 1$ case (incomplete mutual recognition)
- [ ] **Empirical validation**: Design experiments testing calibration predictions

### From Physics Papers
**Reflexive Disequilibrium & Cosmological Phase Change**:
- [ ] Model long-range redshift propagation
- [ ] Identify potential attractor manifolds
- [ ] Simulate early-universe phase transitions

**Dynamic Sufficiency in Cosmological Inference**:
- [ ] Implement computational models of dynamic sufficiency
- [ ] Compare to standard ΛCDM predictions
- [ ] Test against CMB and BAO datasets

---

## Writing Projects (In Progress)

### Fictional Memoir (`write-for-a-month-fictional-memoir.md`)
**Status**: 30 TODO sections for daily writing prompts
**Theme**: Exploring memory and object-relations through fiction
- Days 1-30 unwritten, structured prompts defined

### Zombie Novel (`write-for-a-month-zombie-novel.md`)
**Status**: 30 TODO sections for daily writing prompts  
**Theme**: Zombie as empirical ontology of unfinished death
- Days 1-30 unwritten, structured prompts defined

**Note**: These are creative research projects using narrative as theoretical method.

---

## Corpus Management

### Math Notation (Partially Complete)
- [x] Identify non-standard notation (found 1,118 `$...$` instances)
- [ ] Complete conversion to `$...$` standard (195/1,118 converted)
- [ ] Verify no regressions in LaTeX rendering

### Content Organization
- [x] Remove duplicates (2 pairs removed, 43 files remain)
- [ ] Create inter-document navigation (see-also links based on topics)
- [ ] Build topic index for corpus

### Forgotten Theoretical Fragments
- [ ] **Auto-immunity & individuation**: Simondon-inspired analysis of immune paralysis (fragments in zombie papers)
- [ ] **Directed projections in attention**: Stratified feed coherence model (social media scrolling paper)
- [ ] **Information curvature conservation**: Principle connecting Fisher metric to GR Bianchi identity

---

## Research Directions

### Empirical Studies
- [ ] Neurocognitive testing of information-theoretic stability predictions
- [ ] Social media feed manipulation experiments (attention dynamics)
- [ ] Literary paracosm reproduction studies (Anna Karenina formalization)

### Philosophical Extensions
- [ ] Hermeneutic lineage documentation (philosophy/describing-the-lineage-of-hermeneutics.md)
- [ ] Late Marx as narrative structure (Marxian narrative paper)
- [ ] Liberal subjectivity as information malfunction (kyriarchism paper)

### Media Analysis Applications
- [ ] Phineas & Ferb: Episodic jouissance within corporate liberation (partial)
- [ ] Walking Dead: Empirical ontology of unfinished death (partial)
- [ ] Zombie as ontological category (partial draft exists)

---

## Meta-Research

### Directed Relational Research
Papers exist but methodology needs formalization:
- [ ] **Research as medicine**: Complete formalization of DRR-as-medicine framework
- [ ] **Method documentation**: Write practical guide to DRR methodology
- [ ] **Case studies**: Document examples of DRR in practice

### Repository as Research Object
- [ ] **MCP server implementation**: Make RRPR Interface fully MCP-compatible for agent access
- [ ] **API documentation**: OpenAPI spec for all endpoints
- [ ] **Query language**: Design declarative graph query DSL

---

## Usage Notes

**For Future Sessions**:
1. Review this backlog when planning new work
2. Move completed items to appropriate research notes
3. Add new forgotten ideas as they emerge from conversations
4. Prioritize based on theoretical dependencies and user goals

**Priority Levels** (implicit):
- Infrastructure blocking research → High
- Theoretical foundations → High  
- Applications & experiments → Medium
- Creative writing projects → Low (self-paced)

---

## Related Documents
- `research/docs/guide.corpus-style.md` - Standards for new documents
- `research/docs/spec.relationing-architecture.md` - Architecture TODOs
- `research/docs/report.redundancy.md` - Recent cleanup work
- `plan.replit.md` - System overview and technical specs
