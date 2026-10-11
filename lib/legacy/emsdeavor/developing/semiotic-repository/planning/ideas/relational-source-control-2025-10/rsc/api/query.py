"""
Graph query API endpoints.

These endpoints expose graph traversal operations that implement
core Relationing concepts: pathfinding, closure, neighbor discovery,
and cycle detection.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

from rsc.database import get_db_connection
from rsc import query as rsc_query

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
