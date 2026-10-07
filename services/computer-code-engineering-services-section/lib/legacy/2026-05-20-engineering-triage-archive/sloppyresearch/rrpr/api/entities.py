"""
Entity API endpoints (documents, terms, authors, citations).

These endpoints expose virtual cells representing differentiated
entities within the repository: documents, defined terms, authors,
and citation relationships.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from rrpr.database import get_db_connection
from rrpr.api.utils import dict_factory

router = APIRouter(prefix="/api", tags=["entities"])


@router.get("/documents")
async def list_documents() -> List[Dict[str, Any]]:
    """List all documents with metadata."""
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
async def get_document(doc_id: int) -> Dict[str, Any]:
    """Get document details including all edges."""
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
async def list_terms() -> List[Dict[str, Any]]:
    """List all term definitions."""
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
async def list_authors() -> List[Dict[str, Any]]:
    """List all authors."""
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


@router.get("/authors/contributions")
async def get_author_contributions() -> List[Dict[str, Any]]:
    """Get author contribution metrics (commits, files)."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            r.id,
            r.path as author_path,
            (SELECT e.object_literal FROM edges e 
             WHERE e.subject_id = r.id AND e.predicate = 'has_name' LIMIT 1) as name,
            (SELECT COUNT(*) FROM edges e 
             WHERE e.predicate = 'commit_authored_by' AND e.object_id = r.id) as commit_count
        FROM relcells r
        WHERE r.is_virtual = 1 AND r.path LIKE 'virtual:git-author:%'
        ORDER BY commit_count DESC
    """)
    
    authors = cursor.fetchall()
    conn.close()
    return authors


@router.get("/citations")
async def list_citations() -> List[Dict[str, Any]]:
    """List all citations (internal and external)."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            e.id,
            r1.path as source_path,
            m1.title as source_title,
            e.predicate,
            r2.path as target_path,
            m2.title as target_title,
            e.object_literal
        FROM edges e
        JOIN relcells r1 ON e.subject_id = r1.id
        LEFT JOIN document_metadata m1 ON r1.id = m1.relcell_id
        LEFT JOIN relcells r2 ON e.object_id = r2.id
        LEFT JOIN document_metadata m2 ON r2.id = m2.relcell_id
        WHERE e.predicate IN ('cites_internal', 'cites_external', 'cited_by', 'depends_on')
        ORDER BY r1.path, e.predicate
    """)
    
    citations = cursor.fetchall()
    conn.close()
    return citations
