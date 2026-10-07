"""
Graph query API endpoints.

These endpoints expose graph traversal operations that implement
core Relationing concepts: pathfinding, closure, neighbor discovery,
and cycle detection.
"""

from fastapi import APIRouter, HTTPException, Query as QueryParam
from typing import List, Dict, Any, Optional

from rrpi.database import get_db_connection
from rrpi.api.utils import dict_factory
from rrpi.api.relationing_metadata import relationing_cell
from rrpr import query as rsc_query

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("/path")
async def query_path(from_id: int, to_id: int, max_hops: int = 5, predicates: Optional[List[str]] = None) -> Dict[str, Any]:
    """Find shortest path(s) between two cells."""
    conn = get_db_connection()
    try:
        paths = rsc_query.find_path(conn, from_id, to_id, max_hops, predicates)
        return {
            "query": {"type": "path", "from_id": from_id, "to_id": to_id, "max_hops": max_hops, "predicates": predicates},
            "results": {"paths": paths},
            "metadata": {"path_count": len(paths)}
        }
    finally:
        conn.close()


@router.post("/traverse")
async def query_traverse(
    start_id: int, 
    predicates: Optional[List[str]] = None,
    max_depth: int = 3,
    direction: str = "outgoing"
) -> Dict[str, Any]:
    """Traverse the graph from a starting cell."""
    if direction not in ("outgoing", "incoming", "both"):
        raise HTTPException(status_code=400, detail="direction must be 'outgoing', 'incoming', or 'both'")
    
    conn = get_db_connection()
    try:
        result = rsc_query.traverse(conn, start_id, predicates, max_depth, direction)
        return {
            "query": {"type": "traverse", "start_id": start_id, "predicates": predicates, "max_depth": max_depth, "direction": direction},
            "results": result,
            "metadata": {"cell_count": len(result["cells"]), "edge_count": len(result["edges"])}
        }
    finally:
        conn.close()


@router.post("/closure")
async def query_closure(cell_id: int, predicate: str, direction: str = "outgoing") -> Dict[str, Any]:
    """Compute transitive closure for a specific predicate."""
    if direction not in ("outgoing", "incoming"):
        raise HTTPException(status_code=400, detail="direction must be 'outgoing' or 'incoming'")
    
    conn = get_db_connection()
    try:
        result = rsc_query.closure(conn, cell_id, predicate, direction)
        return {
            "query": {"type": "closure", "cell_id": cell_id, "predicate": predicate, "direction": direction},
            "results": result,
            "metadata": {"cell_count": len(result["cells"]), "edge_count": len(result["edges"])}
        }
    finally:
        conn.close()


@router.get("/neighbors/{cell_id}")
async def query_neighbors(
    cell_id: int,
    direction: str = "both",
    predicates: Optional[str] = None
) -> Dict[str, Any]:
    """Get immediate neighbors of a cell."""
    if direction not in ("outgoing", "incoming", "both"):
        raise HTTPException(status_code=400, detail="direction must be 'outgoing', 'incoming', or 'both'")
    
    predicate_list = predicates.split(",") if predicates else None
    
    conn = get_db_connection()
    try:
        result = rsc_query.neighbors(conn, cell_id, direction, predicate_list)
        return {
            "query": {"type": "neighbors", "cell_id": cell_id, "direction": direction, "predicates": predicate_list},
            "results": result,
            "metadata": {"neighbor_count": len(result["cells"]) - 1}  # Exclude the starting cell
        }
    finally:
        conn.close()


@router.get("/by-mode/{mode}")
async def query_by_mode(mode: str) -> Dict[str, Any]:
    """Query cells by differentiation mode."""
    valid_modes = ["git-tree", "frontmatter", "virtual-synthesis"]
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"mode must be one of {valid_modes}")
    
    conn = get_db_connection()
    try:
        cells = rsc_query.query_by_mode(conn, mode)
        return {
            "query": {"type": "by_mode", "differentiation_mode": mode},
            "results": {"cells": cells},
            "metadata": {"cell_count": len(cells)}
        }
    finally:
        conn.close()


@router.get("/orphans")
async def query_orphans(min_edges: int = 0) -> Dict[str, Any]:
    """Find cells with few or no edges (isolated entities)."""
    conn = get_db_connection()
    try:
        orphans = rsc_query.find_orphans(conn, min_edges)
        return {
            "query": {"type": "orphans", "min_edges": min_edges},
            "results": {"cells": orphans},
            "metadata": {"orphan_count": len(orphans)}
        }
    finally:
        conn.close()


@router.get("/cycles/{predicate}")
async def query_cycles(predicate: str, max_cycle_length: int = 10) -> Dict[str, Any]:
    """Detect cycles for a specific predicate."""
    conn = get_db_connection()
    try:
        cycles = rsc_query.detect_cycles(conn, predicate, max_cycle_length)
        return {
            "query": {"type": "cycles", "predicate": predicate, "max_cycle_length": max_cycle_length},
            "results": {"cycles": cycles},
            "metadata": {"cycle_count": len(cycles)}
        }
    finally:
        conn.close()


@router.get("/terms/{term_id}/defining-documents")
@relationing_cell(
    instantiates_terms=["relation", "recognition"],
    differentiation_modes=["virtual-synthesis", "frontmatter"],
    predicates=["defines"],
    closure_type="relational-traversal",
    narrative="Traverses 'defines' edges to find all documents that explicitly define a term in their frontmatter. Future enhancement: track term mentions in document bodies.",
    examples=["Find all papers defining 'differentiation'"]
)
async def query_term_defining_documents(
    term_id: str
) -> Dict[str, Any]:
    """
    Find all documents that explicitly define a term.
    
    NOTE: This endpoint only returns documents that define the term in their
    frontmatter metadata. Tracking term references/mentions in document bodies
    is a future enhancement (requires body-text scanning and new predicates).
    
    Relationing Semantics:
    - Relation: Traverses 'defines' edges between term (virtual cell) and documents
    - Recognition: Returns recognized documents with their metadata
    """
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    try:
        # Get term info
        cursor.execute("""
            SELECT term_id, label, description
            FROM terms
            WHERE term_id = ?
        """, (term_id,))
        
        term = cursor.fetchone()
        if not term:
            raise HTTPException(status_code=404, detail=f"Term '{term_id}' not found")
        
        # Find documents that define this term
        cursor.execute("""
            SELECT DISTINCT
                r.id,
                r.path,
                m.title,
                m.status,
                m.date_created,
                m.date_modified
            FROM edges e
            JOIN relcells r ON e.subject_id = r.id
            LEFT JOIN document_metadata m ON r.id = m.relcell_id
            WHERE e.predicate = 'defines'
              AND e.object_id IN (
                  SELECT rc.id FROM relcells rc 
                  JOIN terms t ON rc.id = t.relcell_id 
                  WHERE t.term_id = ?
              )
              AND r.is_virtual = 0
            ORDER BY r.path
        """, (term_id,))
        
        defining_docs = cursor.fetchall()
        
        return {
            "term_id": term["term_id"],
            "term_label": term["label"],
            "term_description": term["description"],
            "defining_documents": defining_docs,
            "total_documents": len(defining_docs)
        }
    finally:
        conn.close()


@router.get("/citations/{doc_id}/chains")
@relationing_cell(
    instantiates_terms=["relation", "graph-traversal"],
    differentiation_modes=["frontmatter"],
    predicates=["cites_internal", "cited_by"],
    closure_type="transitive-closure",
    narrative="Recursively traverses citation edges to construct dependency chains with cycle detection.",
    examples=["Find all papers cited by a document (direct and transitive)"]
)
async def query_citation_chains(
    doc_id: int,
    direction: str = QueryParam("outbound", regex="^(outbound|inbound|both)$"),
    max_depth: int = QueryParam(5, ge=1, le=10)
) -> Dict[str, Any]:
    """
    Traverse citation graph to find citation chains.
    
    Relationing Semantics:
    - Relation: Follows citation edges between documents
    - Graph Traversal: Recursive exploration with cycle detection
    - Transitive Closure: Discovers indirect citation relationships
    """
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    try:
        # Get root document
        cursor.execute("""
            SELECT 
                r.id,
                r.path,
                m.title,
                m.status
            FROM relcells r
            LEFT JOIN document_metadata m ON r.id = m.relcell_id
            WHERE r.id = ? AND r.is_virtual = 0
        """, (doc_id,))
        
        root_doc = cursor.fetchone()
        if not root_doc:
            raise HTTPException(status_code=404, detail=f"Document ID {doc_id} not found")
        
        result = {
            "root_document": root_doc,
            "outbound_chains": [],
            "inbound_chains": [],
            "depth_reached": 0,
            "total_documents": 0
        }
        
        # Outbound citations (papers this document cites)
        if direction in ("outbound", "both"):
            cursor.execute("""
                WITH RECURSIVE citation_chain(id, path, depth, chain_path) AS (
                    SELECT 
                        rc.id,
                        rc.path,
                        1 as depth,
                        CAST(? || ' -> ' || rc.path AS TEXT) as chain_path
                    FROM edges e
                    JOIN relcells rc ON e.object_id = rc.id
                    WHERE e.subject_id = ?
                      AND e.predicate IN ('cites_internal', 'depends_on')
                      AND rc.is_virtual = 0
                    
                    UNION ALL
                    
                    SELECT 
                        rc.id,
                        rc.path,
                        cc.depth + 1,
                        cc.chain_path || ' -> ' || rc.path
                    FROM citation_chain cc
                    JOIN edges e ON e.subject_id = cc.id
                    JOIN relcells rc ON e.object_id = rc.id
                    WHERE e.predicate IN ('cites_internal', 'depends_on')
                      AND rc.is_virtual = 0
                      AND cc.depth < ?
                      AND INSTR(cc.chain_path, rc.path) = 0
                )
                SELECT DISTINCT
                    cc.id,
                    cc.path,
                    MIN(cc.depth) as depth,
                    cc.chain_path,
                    m.title,
                    m.status
                FROM citation_chain cc
                LEFT JOIN document_metadata m ON cc.id = m.relcell_id
                GROUP BY cc.id, cc.path, cc.chain_path
                ORDER BY depth, cc.path
            """, (root_doc["path"], doc_id, max_depth))
            
            result["outbound_chains"] = cursor.fetchall()
            if result["outbound_chains"]:
                result["depth_reached"] = max(doc["depth"] for doc in result["outbound_chains"])
        
        # Inbound citations (papers citing this document)
        if direction in ("inbound", "both"):
            cursor.execute("""
                WITH RECURSIVE citation_chain(id, path, depth, chain_path) AS (
                    SELECT 
                        rc.id,
                        rc.path,
                        1 as depth,
                        CAST(rc.path || ' -> ' || ? AS TEXT) as chain_path
                    FROM edges e
                    JOIN relcells rc ON e.subject_id = rc.id
                    WHERE e.object_id = ?
                      AND e.predicate IN ('cites_internal', 'cited_by', 'depends_on')
                      AND rc.is_virtual = 0
                    
                    UNION ALL
                    
                    SELECT 
                        rc.id,
                        rc.path,
                        cc.depth + 1,
                        rc.path || ' -> ' || cc.chain_path
                    FROM citation_chain cc
                    JOIN edges e ON e.object_id = cc.id
                    JOIN relcells rc ON e.subject_id = rc.id
                    WHERE e.predicate IN ('cites_internal', 'cited_by', 'depends_on')
                      AND rc.is_virtual = 0
                      AND cc.depth < ?
                      AND INSTR(cc.chain_path, rc.path) = 0
                )
                SELECT DISTINCT
                    cc.id,
                    cc.path,
                    MIN(cc.depth) as depth,
                    cc.chain_path,
                    m.title,
                    m.status
                FROM citation_chain cc
                LEFT JOIN document_metadata m ON cc.id = m.relcell_id
                GROUP BY cc.id, cc.path, cc.chain_path
                ORDER BY depth, cc.path
            """, (root_doc["path"], doc_id, max_depth))
            
            result["inbound_chains"] = cursor.fetchall()
            if result["inbound_chains"]:
                inbound_depth = max(doc["depth"] for doc in result["inbound_chains"])
                result["depth_reached"] = max(result["depth_reached"], inbound_depth)
        
        result["total_documents"] = len(result["outbound_chains"]) + len(result["inbound_chains"])
        
        return result
    finally:
        conn.close()
