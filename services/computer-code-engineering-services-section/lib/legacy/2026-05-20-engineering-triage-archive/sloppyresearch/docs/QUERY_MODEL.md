# RSC Query Model - Relationing Semantics

## Overview

This document defines how RSC's graph query system operationalizes Relationing concepts, mapping technical primitives to theoretical foundations from "Proposing Relationing."

## Conceptual Mapping: RSC ↔ Relationing

### Core Primitives

| RSC Technical Primitive | Relationing Concept | Semantic Meaning |
|------------------------|---------------------|------------------|
| **RelCell** (row in relcells) | **Act of Differentiation** | An entity that has been distinguished/brought into being |
| **differentiation_mode** | **Mode of Differentiation** | How the entity came to exist (git-tree, frontmatter, virtual-synthesis) |
| **Edge** (subject→predicate→object) | **Relation** | Explicit connection between differentiated entities |
| **Predicate** | **Type of Relation** | The nature/quality of the connection |
| **Virtual Cell** | **Recognition** | Synthesized abstraction from concrete instances |
| **Path** (chain of edges) | **Relational Chain** | Sequence: differentiation → recognition → relation |
| **Transitive Closure** | **Relational Space** | Complete reachability within a relational domain |

### RITM Phases in RSC

The Relational ∞-Topos Modality manifests in RSC operations:

1. **Generation**: Ingestion creates new cells and edges (bringing entities into being)
2. **Fixation**: Persistence in SQLite with provenance (stabilizing entities in the database)
3. **Stabilization**: Query/traversal verifies consistency and explores relational structure

## Query Operations

### 1. Differentiation Queries

**Purpose**: Explore how entities came into being

```python
# Query: All cells differentiated via a specific mode
query_by_mode(differentiation_mode="virtual-synthesis")
→ Returns all synthesized entities (terms, authors, commits)

# Query: Trace differentiation provenance
trace_provenance(cell_id) 
→ Returns the complete chain: source_file → ingestor → cell → edges
```

**Relationing Insight**: Understanding differentiation modes reveals the ontological basis of entities.

### 2. Recognition Queries

**Purpose**: Explore abstractions and virtual entities

```python
# Query: All virtual cells (recognitions) related to a document
recognitions_from(document_id)
→ Returns terms, authors, citations extracted from the document

# Query: Find all documents recognizing a specific term
documents_recognizing(term_id="differentiation")
→ Returns all documents that define or reference "differentiation"
```

**Relationing Insight**: Virtual cells are second-order entities - recognitions produced by reflecting on concrete entities.

### 3. Relational Traversal

**Purpose**: Navigate chains of relation

```python
# Query: Path between two cells
find_path(from_id, to_id, max_hops=5)
→ Returns shortest path(s) through edges

# Query: All cells reachable via specific predicates
traverse(start_id, predicates=["cites_internal", "depends_on"], max_depth=3)
→ Returns subgraph of citation/dependency relations

# Query: Bidirectional exploration
neighbors(cell_id, direction="both", predicate_filter=None)
→ Returns all cells connected to this cell (incoming + outgoing)
```

**Relationing Insight**: Relations form networks; paths reveal how entities mutually constitute each other.

### 4. Stabilization Checks

**Purpose**: Verify consistency and closure

```python
# Query: Transitive closure
closure(cell_id, predicate="depends_on")
→ Returns all cells in the complete dependency tree

# Query: Detect cycles (non-stabilized loops)
detect_cycles(predicate="cites_internal")
→ Returns circular citation chains

# Query: Orphaned entities (non-integrated)
find_orphans(min_edges=0)
→ Returns cells with no connections (failed stabilization)
```

**Relationing Insight**: Stabilization requires reflexive consistency; cycles or orphans indicate unstable regions.

## Query Syntax

### Predicate-Based Filtering

Queries can filter by predicate categories:

```python
# Ontological predicates
predicates = ["has_type", "instance_of", "subclass_of"]

# Temporal predicates  
predicates = ["created_before", "modified_after", "committed_at"]

# Citation predicates
predicates = ["cites_internal", "cites_external", "cited_by"]

# Git predicates
predicates = ["file_at_commit", "commit_parent_of", "authored_by"]
```

### Hop-Limited Traversal

Control exploration depth:

```python
# Immediate neighbors only (1-hop)
traverse(cell_id, max_depth=1)

# Deep exploration (5-hops)
traverse(cell_id, max_depth=5)

# Unbounded (use with caution)
traverse(cell_id, max_depth=None)
```

### Direction Control

```python
# Outgoing edges only (this cell → others)
traverse(cell_id, direction="outgoing")

# Incoming edges only (others → this cell)
traverse(cell_id, direction="incoming")

# Bidirectional (default)
traverse(cell_id, direction="both")
```

## Implementation Requirements

### Backend Functions (rsc/query.py)

1. `find_path(db, from_id, to_id, max_hops)` - Shortest path(s)
2. `traverse(db, start_id, predicates, max_depth, direction)` - Subgraph exploration
3. `closure(db, cell_id, predicate)` - Transitive closure
4. `neighbors(db, cell_id, direction, predicate_filter)` - Adjacent cells
5. `query_by_mode(db, differentiation_mode)` - Filter by mode
6. `find_orphans(db, min_edges)` - Isolated cells
7. `detect_cycles(db, predicate)` - Circular chains

### API Endpoints (app.py)

1. `POST /api/query/path` - Path finding
2. `POST /api/query/traverse` - Subgraph traversal
3. `POST /api/query/closure` - Transitive closure
4. `GET /api/query/neighbors/{cell_id}` - Adjacent cells
5. `GET /api/query/by-mode/{mode}` - Filter by differentiation mode

### CLI Commands (rsc_cli.py)

1. `python rsc_cli.py query path <from> <to>` - Find paths
2. `python rsc_cli.py query traverse <start> --predicates <list>` - Explore subgraph
3. `python rsc_cli.py query closure <cell> --predicate <name>` - Transitive closure
4. `python rsc_cli.py query neighbors <cell>` - Show adjacent cells
5. `python rsc_cli.py query orphans` - Find isolated cells

## Canonical Research Questions

These queries demonstrate Relationing research workflows:

### Q1: Differentiation Chains

"How does the concept of 'differentiation' propagate through the research corpus?"

```python
# Find all documents defining "differentiation"
term_cell = get_cell(path="virtual:term:differentiation")
docs = documents_recognizing(term_cell.id)

# Trace forward: which documents cite those foundational texts?
for doc in docs:
    citations = traverse(doc.id, predicates=["cites_internal"], max_depth=2)
```

### Q2: Recognition Regions

"What are all the virtual entities (recognitions) synthesized from a specific document?"

```python
doc_cell = get_cell(path="txt/scientific-texts/relations/proposing-relationing.md")
virtuals = neighbors(doc_cell.id, direction="outgoing", 
                     predicate_filter=["defines_term", "authored_by", "cites_internal"])
```

### Q3: Stabilization Analysis

"Are there citation cycles (unstable relational structures) in the corpus?"

```python
cycles = detect_cycles(predicate="cites_internal")
if cycles:
    print(f"Found {len(cycles)} circular citation chains (non-stabilized regions)")
```

## Output Schema

All queries return a consistent format:

```python
{
    "query": {
        "type": "path" | "traverse" | "closure",
        "parameters": {...},
        "timestamp": "2025-11-09T19:15:00"
    },
    "results": {
        "cells": [
            {
                "id": 123,
                "path": "...",
                "differentiation_mode": "git-tree",
                "is_virtual": false
            }
        ],
        "edges": [
            {
                "subject_id": 123,
                "predicate": "cites_internal",
                "object_id": 456
            }
        ],
        "paths": [  # For path queries
            {
                "length": 3,
                "cells": [123, 456, 789],
                "edges": [...]
            }
        ]
    },
    "metadata": {
        "cell_count": 42,
        "edge_count": 87,
        "execution_time_ms": 15
    }
}
```

## Next Steps

1. Implement `rsc/query.py` with core traversal functions
2. Add API endpoints to `app.py`
3. Extend `rsc_cli.py` with query commands
4. Create test suite with canonical research questions
5. Build simple web UI for query composition
