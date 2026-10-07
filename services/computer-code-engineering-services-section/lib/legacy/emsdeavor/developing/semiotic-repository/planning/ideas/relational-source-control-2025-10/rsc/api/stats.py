"""
Statistics API endpoints.
"""

from fastapi import APIRouter
from typing import Dict
import sqlite3

from rsc.database import get_db_connection
from rsc.api.utils import dict_factory

router = APIRouter(prefix="/api", tags=["statistics"])


@router.get("/stats")
async def get_stats() -> Dict[str, int]:
    """Get database statistics."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute("SELECT COUNT(*) as count FROM relcells WHERE is_virtual = 0")
    stats["documents"] = cursor.fetchone()["count"]
    
    cursor.execute("SELECT COUNT(*) as count FROM relcells WHERE is_virtual = 1")
    stats["virtual_cells"] = cursor.fetchone()["count"]
    
    cursor.execute("SELECT COUNT(*) as count FROM edges")
    stats["edges"] = cursor.fetchone()["count"]
    
    cursor.execute("SELECT COUNT(*) as count FROM terms")
    stats["terms"] = cursor.fetchone()["count"]
    
    cursor.execute("SELECT COUNT(*) as count FROM authors")
    stats["authors"] = cursor.fetchone()["count"]
    
    conn.close()
    return stats
