+++
id = "spec.relationing-architecture"
title = "Relationing-Aligned API Architecture"
status = "active"
document_type = "specification"
topics = ["api", "architecture"]
+++


## Overview

The RRPR Interface API is designed to **directly embody Relationing theory**. The code structure, URL paths, and endpoint organization are not arbitrary technical choices—they instantiate the research itself.

This document explains how the API architecture maps to Relationing concepts, making the theoretical foundations visible in the codebase.

## Core Principle: Code as Theory

**The API structure mirrors the phases of Relationing:**
1. **Differentiation** - Distinguishing regions (files, commits, concepts)
2. **Recognition** - Stabilizing differentiated regions as queryable entities
3. **Relation** - Edges connecting recognized cells
4. **Stabilization** - Closure operations producing fixed points

Each endpoint explicitly declares which concepts it instantiates via metadata decorators.

## Metadata Layer

### Purpose
Make theoretical foundations **explicit and queryable** rather than implicit in implementation.

### Implementation (`rrpr/api/relationing_metadata.py`)

```python
@relationing_cell(
    instantiates_terms=["recognition", "differentiation"],
    differentiation_modes=["frontmatter"],
    predicates=["has_metadata", "authored_by"],
    closure_type="recognition",
    narrative="Enumerates recognized documents as differentiated regions..."
)
async def list_documents():
    """Recognition: Documents are differentiated regions that have been recognized"""
```

### Metadata Fields

| Field | Purpose | Example Values |
|-------|---------|----------------|
| `instantiates_terms` | Which Relationing concepts this endpoint embodies | `["recognition", "differentiation"]` |
| `differentiation_modes` | Which types of cells it queries | `["git-tree", "frontmatter", "virtual-synthesis"]` |
| `predicates` | Which relational edges it traverses | `["cites_internal", "authored_by"]` |
| `closure_type` | Type of stabilization operation | `"recognition"`, `"transitive"`, `None` |
| `narrative` | Human-readable explanation of Relationing semantics | See examples below |
| `examples` | Concrete instances from the repository | `["Proposing Relationing with 16 terms"]` |

### Zero Runtime Overhead
Decorators attach metadata to functions **without affecting execution**. They're declarative documentation that's machine-queryable.

## Concept-Scoped Routers

### Recognition Router (`rrpr/api/recognition.py`)

**Theoretical Foundation:**
Recognition is the process by which differentiated regions stabilize into queryable entities.

**Endpoints:**

#### `GET /api/recognition/documents`
- **Instantiates:** recognition, differentiation
- **Queries:** frontmatter-differentiated cells
- **Closure:** recognition (enumerates recognized document set)
- **Narrative:** "Documents are differentiated regions that have been recognized through frontmatter parsing"

#### `GET /api/recognition/terms`
- **Instantiates:** recognition, reflexive-definition
- **Queries:** virtual-synthesis cells
- **Closure:** recognition
- **Narrative:** "Terms are self-referential: the research defines its own conceptual vocabulary"

#### `GET /api/recognition/authors`
- **Instantiates:** recognition, authorship
- **Queries:** frontmatter + virtual-synthesis
- **Closure:** recognition
- **Narrative:** "Authors are agents who produce differentiated regions (documents)"

### Relation Router (`rrpr/api/relation.py`)

**Theoretical Foundation:**
Relations are directed, typed edges connecting recognized cells in the graph.

**Endpoints:**

#### `GET /api/relation/citations`
- **Instantiates:** relation, reference
- **Predicates:** cites_internal, cites_external, cited_by, depends_on
- **Narrative:** "Citations are edges forming a dependency graph of ideas"

#### `GET /api/relation/contributions`
- **Instantiates:** relation, authorship, agency
- **Predicates:** commit_authored_by, has_name
- **Narrative:** "Maps authors to their produced commits, revealing collaborative production"

## URL Structure as Theory Visualization

```
/api/
├── recognition/          # Recognized entities (stable differentiated regions)
│   ├── documents         # Frontmatter-differentiated documents
│   ├── terms             # Virtually-synthesized term definitions
│   └── authors           # Recognized authorship agents
│
├── relation/             # Relational edges (typed predicates)
│   ├── citations         # Citation edges (reference relations)
│   └── contributions     # Authorship edges (production relations)
│
├── metadata/             # Theory discovery (make foundations queryable)
│   ├── relationing       # Complete metadata registry
│   ├── relationing/terms       # Which endpoints instantiate which terms
│   ├── relationing/predicates  # Which endpoints query which predicates
│   ├── relationing/modes       # Which endpoints query which differentiation modes
│   └── relationing/summary     # Coverage statistics
│
├── query/                # Graph traversal operations
│   └── ...               # (infrastructure layer)
│
└── git/                  # Git-specific operations  
    └── ...               # (infrastructure layer)
```

## Metadata Discovery Endpoints

The metadata layer is **itself queryable**, making the API self-documenting at the theoretical level.

### `GET /api/metadata/relationing/summary`

Returns statistics about how well the API embodies the research:

```json
{
  "annotated_endpoints": 6,
  "instantiated_terms": ["recognition", "differentiation", "relation", ...],
  "exposed_predicates": ["cites_internal", "authored_by", ...],
  "queryable_modes": ["frontmatter", "virtual-synthesis"],
  "coverage": {
    "total_terms": 7,
    "total_predicates": 10,
    "total_modes": 2
  }
}
```

### `GET /api/metadata/relationing/terms`

Reverse index: which endpoints instantiate which Relationing concepts?

```json
{
  "recognition": [
    "recognition.list_documents",
    "recognition.get_document",
    "recognition.list_terms",
    "recognition.list_authors"
  ],
  "differentiation": ["recognition.list_documents"],
  "relation": ["recognition.get_document", "relation.list_citations", ...]
}
```

### `GET /api/metadata/relationing/predicates`

Which endpoints expose which relational edges?

```json
{
  "cites_internal": [
    "recognition.list_documents",
    "relation.list_citations"
  ],
  "authored_by": [
    "recognition.list_documents",
    "recognition.list_authors"
  ]
}
```

## Design Decisions

### Why Decorators?
- **Explicit over implicit**: Theory annotations visible in code
- **Separation of concerns**: Metadata doesn't affect execution
- **Machine-queryable**: Build tools that reason about theoretical foundations
- **Self-documenting**: Code explains which concepts it embodies

### Why Concept-Scoped Routers?
- **URL structure mirrors theory**: Paths reflect Relationing phases
- **Theoretical navigation**: Users can explore by concept, not just entity type
- **Clear boundaries**: Recognition vs relation vs stabilization
- **Extensible**: Adding new Relationing concepts = adding new routers

### Why Metadata Discovery?
- **Self-reflection**: API can describe its own theoretical foundations
- **Automated verification**: Check coverage of Relationing concepts
- **Educational**: Users learn theory by exploring metadata
- **Integration-ready**: External tools can query theoretical structure

## Implementation Guidelines

### Adding a New Endpoint

1. **Identify the Relationing concept** it embodies
2. **Choose the appropriate router** (recognition, relation, stabilization, etc.)
3. **Add the `@relationing_cell` decorator** with complete metadata
4. **Write a narrative docstring** explaining Relationing semantics
5. **Verify metadata exposure** via `/api/metadata/relationing/summary`

Example:

```python
@router.get("/documents")
@relationing_cell(
    instantiates_terms=["recognition", "differentiation"],
    differentiation_modes=["frontmatter"],
    predicates=["has_metadata", "authored_by"],
    closure_type="recognition",
    narrative="Enumerates recognized documents as differentiated regions"
)
async def list_documents():
    """
    Recognition: Documents are differentiated regions that have been recognized.
    
    Each document represents stable recognition of Markdown content with
    extracted TOML frontmatter metadata.
    """
    # Implementation...
```

### Adding a New Concept Router

If you're adding a new Relationing phase (e.g., `stabilization`):

1. Create `rrpr/api/stabilization.py`
2. Define router: `router = APIRouter(prefix="/api/stabilization", tags=["stabilization"])`
3. Add endpoints with `@relationing_cell` decorators
4. Register in `scripts/rrpr-web.py` under concept-aligned routers
5. Document in this file

## Theoretical Coverage (Current State)

### Instantiated Terms (7)
- recognition
- differentiation
- relation
- reflexive-definition
- authorship
- agency
- reference

### Exposed Predicates (10)
- has_metadata
- authored_by
- cites_internal
- cites_external
- cited_by
- depends_on
- defines_term
- introduced_in
- commit_authored_by
- has_name

### Queryable Differentiation Modes (2)
- frontmatter (Markdown documents with TOML metadata)
- virtual-synthesis (Terms, authors, commits synthesized from other cells)

### Missing (Future Work)
- **git-tree mode**: Add endpoints querying git-tree differentiated cells
- **Stabilization router**: Closure operations, fixed points, transitive closures
- **Differentiation router**: Explicit differentiation operations
- **More predicates**: Expand predicate coverage (see `rrpr/predicates.py` for full list)

## Benefits of This Architecture

1. **Code explains itself theoretically**: New contributors see how tooling embodies research
2. **Queryable foundations**: Tools can reason about which endpoints instantiate which concepts
3. **Alignment verification**: Automated checks ensure API stays true to theory
4. **Educational**: API structure teaches Relationing by example
5. **Extensible**: Adding new concepts follows clear patterns
6. **MCP-ready**: Metadata layer enables remote agent understanding

## Related Documentation

- **Theory**: `research/discipline/mathematics/relationing/category-theory/proposing-relationing/papers/proposing-relationing.md` (foundational treatise)
- **Graph Schema**: `research/docs/spec.schema.md` (RelCell, Edge, Provenance models)
- **Query Semantics**: `research/docs/spec.query-model.md` (graph operations in Relationing terms)
- **Predicates**: `rrpr/predicates.py` (complete predicate registry)
- **Agent Guidelines**: `guidelines.agents.md` (how agents should work with the repository)

## Conclusion

This architecture makes the RRPR Interface **transparently aligned with Relationing theory**. Every endpoint is a window into the research, every URL path reflects theoretical structure, and every decorator makes foundations explicit.

The code doesn't just *implement* the theory—it **instantiates** it.
