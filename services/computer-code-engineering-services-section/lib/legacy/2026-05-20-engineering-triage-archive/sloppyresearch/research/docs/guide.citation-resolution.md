+++
id = "guide.citation-resolution"
title = "Citation Resolution Rules for RRPR"
status = "active"
document_type = "guide"
topics = ["citations", "graph"]
+++


**Purpose**: Defines how citations (internal and external) are normalized, resolved, and represented as virtual cells in the knowledge graph.

---

## Core Principle

**Citations create edges**: Every citation, whether to an internal document or external publication, creates explicit edges in the knowledge graph, enabling traversal and analysis of the research network.

---

## Internal Citation Resolution

### Document ID Normalization

All internal citations must reference valid document IDs from the corpus.

#### ID Format Rules

```
^[a-z0-9\-\.]+$
```

- **Lowercase only**: All IDs use lowercase letters
- **Hyphen-separated**: Words separated by hyphens
- **Dot-namespacing**: Use dots for hierarchical organization (e.g., `theorem.stability-conservation`)
- **No spaces**: Replace with hyphens
- **No special chars**: Only letters, numbers, hyphens, dots

#### Examples

**Valid:**
```
proposing-relationing
theorem.information-theoretic-stability  
stability-optimization-in-artificial-agents
deriving-a-reflexive-infinity-topos
```

**Invalid:**
```
Proposing_Relationing          # uppercase + underscore
describing stability           # space
theorem:stability              # colon
```

### Resolution Process

When ingesting a document with `cites_internal = ["doc-id-1", "doc-id-2"]`:

1. **Validate format**: Check each ID matches `^[a-z0-9\-\.]+$`
2. **Resolve target**: Look up corresponding RelCell in database
3. **Create edges**:
   - `(source_doc) --[cites_internal]--> (target_doc)`  
   - `(target_doc) --[cited_by]--> (source_doc)` (inverse)
4. **Log failures**: If ID not found, record in ingestion report

### Broken Reference Handling

**Options for broken internal citations:**

1. **Auto-fix**: If document exists with similar ID (edit distance < 3), suggest correction
2. **Fuzzy match**: Search for documents with similar titles/content
3. **Report**: Log as validation error for manual review
4. **Placeholder**: Create `virtual:unresolved-reference.{id}` cell with status "needs-resolution"

**Example auto-fix:**
```toml
# Found in frontmatter:
cites_internal = ["proposing-reflexive-existance"]  # typo

# Auto-corrected to:
cites_internal = ["proposing-a-reflexive-existence"]  # correct ID
```

---

## External Citation Resolution

External citations create virtual cells for publications and their authors.

### Citation Key Format

**Standard format**: `author:year:short-title`

```
deloria:1999:spirit-and-reason
maclane:1998:categories
christiano:2017:deep-reinforcement-learning
```

**Rules:**
- **author**: Last name (normalized, lowercase, no spaces)
- **year**: Publication year (4 digits)
- **short-title**: 2-4 keywords from title (hyphens, lowercase)
- **Colons**: Separate components
- **Multi-author**: Use first author only in key

### Virtual Cell Structure

Each external citation creates **3 types of virtual cells**:

#### 1. Publication Virtual Cell

**ID format**: `virtual:publication.{citation_key}`

**Example:**
```
virtual:publication.deloria:1999:spirit-and-reason
```

**Edges from publication cell:**
- `(publication) --[has_title]--> "Power and Place: Indian Education in America"`
- `(publication) --[has_year]--> "1999"`
- `(publication) --[has_venue]--> "Fulcrum Publishing"`
- `(publication) --[has_doi]--> "10.1234/example"`
- `(publication) --[has_url]--> "https://..."`

#### 2. Author Virtual Cells

**ID format**: `virtual:author.{normalized-name}`

**Normalization rules:**
- Lowercase
- Spaces → hyphens
- Remove periods, commas, apostrophes
- Keep Unicode letters (for non-ASCII names)

**Examples:**
```
Vine Deloria Jr.    → virtual:author.vine-deloria-jr
Saunders Mac Lane   → virtual:author.saunders-mac-lane
François Lamarche   → virtual:author.francois-lamarche
```

**Edges from author cell:**
- `(author) --[has_name]--> "Vine Deloria Jr."` (display name)
- `(author) --[authored]--> (publication)` (authorship relation)

#### 3. Citation Relation Edges

**From citing document to publication:**
```
(document) --[cites_external]--> (publication)
```

**From document to authors (optional enrichment):**
```
(document) --[cites_author]--> (author)
```

**From publication to authors:**
```
(publication) --[authored_by]--> (author)
```

---

## Bibliography.bib Integration

### Purpose

`ref/bibliography.bib` is the **canonical source** for external citation metadata. All `[cites_external](cites_external)` blocks should reconcile against it.

### Workflow

#### 1. Populate bibliography.bib

```bibtex
@book{deloria:1999:spirit-and-reason,
  author = {Vine Deloria Jr. and Daniel R. Wildcat},
  title = {Power and Place: Indian Education in America},
  year = {1999},
  publisher = {Fulcrum Publishing},
  isbn = {1-55591-390-1}
}

@book{maclane:1998:categories,
  author = {Saunders Mac Lane},
  title = {Categories for the Working Mathematician},
  year = {1998},
  publisher = {Springer},
  edition = {2nd},
  doi = {10.1007/978-1-4757-4721-8}
}
```

#### 2. Parse bibliography.bib

Tool: `scripts/parse_bibliography.py`

- Reads BibTeX entries
- Converts to `[cites_external](cites_external)` TOML format
- Normalizes citation keys to `author:year:short-title` format
- Extracts author names, splits multi-author fields

#### 3. Reconcile Citations

For each `[cites_external](cites_external)` in corpus frontmatter:

1. **Check key exists** in bibliography.bib
2. **Match metadata**: Ensure author/title/year consistency
3. **Enrich missing fields**: Pull DOI, ISBN, venue from .bib if missing
4. **Report conflicts**: If metadata differs, log for manual review

#### 4. Add Missing Citations

If corpus cites publication not in bibliography.bib:
- Extract citation from frontmatter `[cites_external](cites_external)`
- Generate BibTeX entry
- Add to bibliography.bib
- Commit to git with message: `Add citation: {key}`

---

## Predicate Definitions for Citations

### Internal Citations

| Predicate | Domain | Range | Description |
|-----------|--------|-------|-------------|
| `cites_internal` | RelCell (doc) | RelCell (doc) | Document cites another internal document |
| `cited_by` | RelCell (doc) | RelCell (doc) | Inverse of `cites` |

### External Citations

| Predicate | Domain | Range | Description |
|-----------|--------|-------|-------------|
| `cites_external` | RelCell (doc) | RelCell (publication) | Document cites external publication |
| `authored_by` | RelCell (publication) | RelCell (author) | Publication authored by person |
| `authored` | RelCell (author) | RelCell (publication) | Inverse of `authored_by` |
| `cites_author` | RelCell (doc) | RelCell (author) | Document transitively cites author (optional) |

### Metadata Predicates (for virtual cells)

| Predicate | Domain | Range | Description |
|-----------|--------|-------|-------------|
| `has_title` | RelCell (publication) | Literal[str] | Publication title |
| `has_year` | RelCell (publication) | Literal[int] | Publication year |
| `has_venue` | RelCell (publication) | Literal[str] | Publisher/journal/conference |
| `has_doi` | RelCell (publication) | Literal[str] | Digital Object Identifier |
| `has_url` | RelCell (publication) | Literal[str] | Web link |
| `has_isbn` | RelCell (publication) | Literal[str] | ISBN for books |
| `has_name` | RelCell (author) | Literal[str] | Author display name |

---

## Citation Graph Queries

### Find All Papers Citing a Document

```sql
SELECT source.path, source_meta.title
FROM edges
JOIN relcells source ON edges.subject_id = source.id
LEFT JOIN document_metadata source_meta ON source.id = source_meta.relcell_id
WHERE edges.predicate = 'cites_internal' 
  AND edges.object_id = (SELECT id FROM relcells WHERE path = 'research/discipline/mathematics/relationing/category-theory/proposing-relationing/papers/proposing-relationing.md')
ORDER BY source.path
```

### Find All Documents Citing Deloria

```sql
SELECT doc.path, doc_meta.title
FROM edges e1
JOIN relcells doc ON e1.subject_id = doc.id
LEFT JOIN document_metadata doc_meta ON doc.id = doc_meta.relcell_id
JOIN edges e2 ON e1.object_id = e2.subject_id  
WHERE e1.predicate = 'cites_external'
  AND e2.predicate = 'authored_by'
  AND e2.object_id = (SELECT id FROM relcells WHERE path = 'virtual:author.vine-deloria-jr')
ORDER BY doc.path
```

### Find Most Cited Internal Documents

```sql
SELECT target.path, target_meta.title, COUNT(*) as citation_count
FROM edges
JOIN relcells target ON edges.object_id = target.id
LEFT JOIN document_metadata target_meta ON target.id = target_meta.relcell_id
WHERE edges.predicate = 'cites_internal'
GROUP BY target.id
ORDER BY citation_count DESC
LIMIT 10
```

### Find Most Cited Authors

```sql
SELECT author.path, name_edge.object_literal as author_name, COUNT(DISTINCT doc.id) as citing_docs
FROM relcells author
JOIN edges name_edge ON author.id = name_edge.subject_id AND name_edge.predicate = 'has_name'
JOIN edges pub_edge ON author.id = pub_edge.subject_id AND pub_edge.predicate = 'authored'
JOIN edges cite_edge ON pub_edge.object_id = cite_edge.object_id AND cite_edge.predicate = 'cites_external'
JOIN relcells doc ON cite_edge.subject_id = doc.id
WHERE author.path LIKE 'virtual:author.%'
GROUP BY author.id
ORDER BY citing_docs DESC
LIMIT 10
```

---

## Implementation Tools

### scripts/audit_citations.py

Scans all `cites_internal` fields and reports:
- Broken references (ID not found)
- Suggested fixes (fuzzy matches)
- Missing inverse `cited_by` edges
- Citation consistency (ID format violations)

### scripts/parse_bibliography.py

Parses `ref/bibliography.bib` and:
- Extracts all BibTeX entries
- Converts to TOML `[cites_external](cites_external)` format
- Normalizes citation keys
- Generates author virtual cell IDs
- Outputs JSON mapping: `{citation_key: {authors, title, year, ...}}`

### scripts/resolve_citations.py

Main citation resolution script:
1. Load bibliography.bib metadata
2. For each document in corpus:
   - Validate `cites_internal` references
   - Auto-fix broken IDs (with confirmation)
   - Reconcile `cites_external` against bibliography
   - Create missing virtual cells
   - Emit `cites`, `cited_by`, `cites_external`, `authored_by` edges
3. Generate ingestion report

---

## Related Documents

- `research/docs/policy.archival.md` - Document lifecycle management
- `research/docs/guide.corpus-style.md` - Frontmatter format standards
- `ref/bibliography.bib` - Canonical external citation source
- `rrpr/predicates.py` - Predicate definitions
- `rrpr/virtual_cells.py` - Virtual cell ID generation
