"""
Graph data API endpoints.

These endpoints expose the complete knowledge graph structure
for visualization and export.
"""

from fastapi import APIRouter
from typing import Dict, Any

from code.library.database import get_db_connection
from code.library.api.utils import dict_factory

router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph")
async def get_graph() -> Dict[str, Any]:
    """Get the complete knowledge graph."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM relcells")
    nodes = cursor.fetchall()
    
    cursor.execute("""
        SELECT 
            e.id,
            e.subject_id,
            e.predicate,
            e.object_id,
            e.object_literal,
            p.source_path,
            p.ingestor
        FROM edges e
        JOIN provenance p ON e.provenance_id = p.id
    """)
    edges = cursor.fetchall()
    
    conn.close()
    
    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    }
