"""
Recognition API endpoints.

Recognition: The process by which differentiated regions stabilize
into queryable entities. These endpoints enumerate and retrieve
recognized cells in the repository graph.

Theoretical Foundation:
- Documents are recognized through frontmatter parsing
- Terms are recognized through definition extraction
- Authors are recognized through metadata and Git history
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from code.library.database import get_db_connection
from code.library.api.utils import dict_factory
from code.library.api.relationing_metadata import relationing_cell

router = APIRouter(prefix="/api/recognition", tags=["recognition"])


@router.get("/documents")
@relationing_cell(
    instantiates_terms=["recognition", "differentiation"],
    differentiation_modes=["frontmatter"],
    predicates=["has_metadata", "authored_by", "cites_internal"],
    closure_type="recognition",
    narrative="Enumerates all recognized documents as differentiated regions in the research space. Each document represents a stable recognition of Markdown content with extracted metadata.",
    examples=["Proposing Relationing document with 16 term definitions"]
)
async def list_documents() -> List[Dict[str, Any]]:
    """
    List all recognized documents with metadata.
    
    Relationing Semantics:
    - Recognition: Documents are differentiated regions that have been recognized
    - Differentiation: Each document is distinguished by its path and frontmatter
    - Stabilization: Documents persist as queryable entities in the graph
    """
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            r.id,
            r.branch,
            r.commit_hash,
            r.path,
            m.title,
            m.status,
            m.date_created,
            m.date_modified
        FROM relcells r
        LEFT JOIN document_metadata m ON r.id = m.relcell_id
        WHERE r.is_virtual = 0
        ORDER BY r.ingested_at DESC
    """)
    
    docs = cursor.fetchall()
    conn.close()
    return docs


@router.get("/documents/{doc_id}")
@relationing_cell(
    instantiates_terms=["recognition", "relation"],
    differentiation_modes=["frontmatter"],
    predicates=["has_metadata", "authored_by", "defines_term", "cites_internal"],
    narrative="Retrieves a single recognized document with its complete relational structure (all edges).",
    examples=["Document ID 42 with edges to 3 authors and 5 cited publications"]
)
async def get_document(doc_id: int) -> Dict[str, Any]:
    """
    Get a recognized document with its complete relational structure.
    
    Relationing Semantics:
    - Recognition: Retrieves a specific differentiated region
    - Relation: Includes all edges connecting this document to other cells
    - Graph traversal: One-hop neighborhood of the document cell
    """
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            r.*,
            m.title,
            m.status,
            m.date_created,
            m.date_modified
        FROM relcells r
        LEFT JOIN document_metadata m ON r.id = m.relcell_id
        WHERE r.id = ? AND r.is_virtual = 0
    """, (doc_id,))
    
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    cursor.execute("""
        SELECT e.predicate, e.object_literal, r.path as object_path
        FROM edges e
        LEFT JOIN relcells r ON e.object_id = r.id
        WHERE e.subject_id = ?
    """, (doc_id,))
    
    doc["edges"] = cursor.fetchall()
    conn.close()
    return doc


@router.get("/terms")
@relationing_cell(
    instantiates_terms=["recognition", "reflexive-definition"],
    differentiation_modes=["virtual-synthesis"],
    predicates=["defines_term", "introduced_in"],
    closure_type="recognition",
    narrative="Enumerates all defined terms as virtual cells synthesized from document frontmatter. Terms are self-referential: the research defines its own conceptual vocabulary.",
    examples=["differentiation", "recognition", "relation", "stabilization"]
)
async def list_terms() -> List[Dict[str, Any]]:
    """
    List all defined terms in the research.
    
    Relationing Semantics:
    - Recognition: Terms are recognized through definition extraction
    - Virtual Synthesis: Terms exist as virtual cells, not physical files
    - Reflexivity: The research defines and uses its own terms
    """
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            term_id,
            label,
            description,
            aliases,
            virtual_path,
            introduced_in_path,
            introduced_in_title
        FROM v_term_definitions
        ORDER BY label
    """)
    
    terms = cursor.fetchall()
    conn.close()
    return terms


@router.get("/authors")
@relationing_cell(
    instantiates_terms=["recognition", "authorship"],
    differentiation_modes=["frontmatter", "virtual-synthesis"],
    predicates=["authored_by", "has_name"],
    closure_type="recognition",
    narrative="Enumerates all recognized authors from document frontmatter. Authors are agents who produce differentiated regions (documents).",
    examples=["emsenn as document author", "Git contributors as commit authors"]
)
async def list_authors() -> List[Dict[str, Any]]:
    """
    List all recognized authors.
    
    Relationing Semantics:
    - Recognition: Authors are recognized from document metadata
    - Agency: Authors are agents who produce differentiated content
    - Virtual Synthesis: Authors exist as virtual cells derived from documents
    """
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT author_id, name, aliases, virtual_path, branch, commit_hash
        FROM v_authors
        ORDER BY name
    """)
    
    authors = cursor.fetchall()
    conn.close()
    return authors
