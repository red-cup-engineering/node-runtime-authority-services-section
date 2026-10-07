"""
Git-related API endpoints (files, commits, branches).

These endpoints expose Git repository metadata extracted
from the repository structure and history.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from rrpi.database import get_db_connection
from rrpi.api.utils import dict_factory

router = APIRouter(prefix="/api", tags=["git"])


@router.get("/files")
async def list_files(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """List all repository files."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            id, branch, commit_hash, path, file_type, 
            mime_type, size_bytes, checksum, ingested_at
        FROM relcells
        WHERE is_virtual = 0
        ORDER BY path
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    files = cursor.fetchall()
    conn.close()
    return files


@router.get("/files/{file_id}")
async def get_file(file_id: int) -> Dict[str, Any]:
    """Get file details with edges."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, branch, commit_hash, path, file_type, 
               mime_type, size_bytes, checksum, ingested_at
        FROM relcells
        WHERE id = ? AND is_virtual = 0
    """, (file_id,))
    
    file = cursor.fetchone()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get edges
    cursor.execute("""
        SELECT e.predicate, e.object_literal, r.path as object_path
        FROM edges e
        LEFT JOIN relcells r ON e.object_id = r.id
        WHERE e.subject_id = ?
    """, (file_id,))
    
    file["edges"] = cursor.fetchall()
    conn.close()
    return file


@router.get("/commits")
async def list_commits(limit: int = 50) -> List[Dict[str, Any]]:
    """List all Git commits."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            r.id,
            r.path as commit_path,
            r.ingested_at,
            (SELECT e.object_literal FROM edges e 
             WHERE e.subject_id = r.id AND e.predicate = 'commit_message' LIMIT 1) as message,
            (SELECT e.object_literal FROM edges e 
             WHERE e.subject_id = r.id AND e.predicate = 'committed_at' LIMIT 1) as timestamp,
            (SELECT r2.path FROM edges e 
             JOIN relcells r2 ON e.object_id = r2.id 
             WHERE e.subject_id = r.id AND e.predicate = 'commit_authored_by' LIMIT 1) as author_path
        FROM relcells r
        WHERE r.is_virtual = 1 AND r.path LIKE 'virtual:commit:%'
        ORDER BY r.ingested_at DESC
        LIMIT ?
    """, (limit,))
    
    commits = cursor.fetchall()
    
    # Add short SHA
    for commit in commits:
        commit['sha'] = commit['commit_path'].replace('virtual:commit:', '')[:8]
    
    conn.close()
    return commits


@router.get("/commits/{commit_sha}")
async def get_commit(commit_sha: str) -> Dict[str, Any]:
    """Get commit details with edges."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    # Find commit (match full SHA or short SHA)
    cursor.execute("""
        SELECT id, path, ingested_at
        FROM relcells
        WHERE is_virtual = 1 AND path LIKE ?
    """, (f"virtual:commit:{commit_sha}%",))
    
    commit = cursor.fetchone()
    if not commit:
        raise HTTPException(status_code=404, detail="Commit not found")
    
    # Get all edges
    cursor.execute("""
        SELECT e.predicate, e.object_literal, r.path as object_path
        FROM edges e
        LEFT JOIN relcells r ON e.object_id = r.id
        WHERE e.subject_id = ?
    """, (commit['id'],))
    
    commit["edges"] = cursor.fetchall()
    commit['sha'] = commit['path'].replace('virtual:commit:', '')
    conn.close()
    return commit


@router.get("/branches")
async def list_branches() -> List[Dict[str, Any]]:
    """List all Git branches."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            r.id,
            r.path as branch_path,
            (SELECT e.object_literal FROM edges e 
             WHERE e.subject_id = r.id AND e.predicate = 'has_name' LIMIT 1) as name,
            (SELECT COUNT(*) FROM edges e 
             WHERE e.predicate = 'commit_on_branch' AND e.object_id = r.id) as commit_count
        FROM relcells r
        WHERE r.is_virtual = 1 AND r.path LIKE 'virtual:branch:%'
        ORDER BY commit_count DESC
    """)
    
    branches = cursor.fetchall()
    conn.close()
    return branches
