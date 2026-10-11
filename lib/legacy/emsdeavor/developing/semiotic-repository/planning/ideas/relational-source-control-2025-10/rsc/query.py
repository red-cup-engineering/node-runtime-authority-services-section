"""
Graph traversal operations for the Relationing Research Program Repository.

These functions enable navigation through the repository's knowledge graph,
operationalizing Relationing concepts (differentiation, recognition, relation,
stabilization) as query primitives.

The repository is the research. These operations help you explore its structure.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import sqlite3
from collections import deque


def find_path(
    conn: sqlite3.Connection,
    from_id: int,
    to_id: int,
    max_hops: int = 5,
    predicate_filter: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Find shortest path(s) between two cells using breadth-first search.
    
    Args:
        conn: Database connection
        from_id: Starting cell ID
        to_id: Target cell ID
        max_hops: Maximum path length to explore
        predicate_filter: Optional list of predicates to traverse
        
    Returns:
        List of paths, each containing cells and edges
    """
    if from_id == to_id:
        return [{
            "length": 0,
            "cells": [from_id],
            "edges": []
        }]
    
    cursor = conn.cursor()
    
    # BFS to find shortest path
    queue = deque([(from_id, [from_id], [])])  # (current_id, path_cells, path_edges)
    visited = {from_id}
    found_paths = []
    min_length = float('inf')
    
    while queue:
        current_id, path_cells, path_edges = queue.popleft()
        
        # Stop if path too long or we found shorter paths
        if len(path_cells) > max_hops + 1 or len(path_cells) > min_length:
            continue
        
        # Get outgoing edges from current cell
        if predicate_filter:
            placeholders = ','.join('?' * len(predicate_filter))
            cursor.execute(f"""
                SELECT object_id, predicate 
                FROM edges 
                WHERE subject_id = ? AND object_id IS NOT NULL 
                  AND predicate IN ({placeholders})
            """, [current_id] + predicate_filter)
        else:
            cursor.execute("""
                SELECT object_id, predicate 
                FROM edges 
                WHERE subject_id = ? AND object_id IS NOT NULL
            """, (current_id,))
        
        for obj_id, predicate in cursor.fetchall():
            if obj_id == to_id:
                # Found a path!
                new_path = {
                    "length": len(path_cells),
                    "cells": path_cells + [obj_id],
                    "edges": path_edges + [{
                        "subject_id": current_id,
                        "predicate": predicate,
                        "object_id": obj_id
                    }]
                }
                found_paths.append(new_path)
                min_length = min(min_length, len(path_cells))
            elif obj_id not in visited:
                visited.add(obj_id)
                queue.append((
                    obj_id,
                    path_cells + [obj_id],
                    path_edges + [{
                        "subject_id": current_id,
                        "predicate": predicate,
                        "object_id": obj_id
                    }]
                ))
    
    # Return only shortest paths
    if found_paths:
        shortest_length = min(p["length"] for p in found_paths)
        return [p for p in found_paths if p["length"] == shortest_length]
    
    return []


def traverse(
    conn: sqlite3.Connection,
    start_id: int,
    predicates: Optional[List[str]] = None,
    max_depth: int = 3,
    direction: str = "outgoing"
) -> Dict[str, Any]:
    """
    Traverse the graph from a starting cell, returning a subgraph.
    
    Args:
        conn: Database connection
        start_id: Starting cell ID
        predicates: Optional list of predicates to follow
        max_depth: Maximum depth to traverse
        direction: "outgoing", "incoming", or "both"
        
    Returns:
        Dictionary with cells and edges in the subgraph
    """
    cursor = conn.cursor()
    
    visited_cells = {start_id}
    subgraph_edges = []
    queue = deque([(start_id, 0)])  # (cell_id, depth)
    
    while queue:
        current_id, depth = queue.popleft()
        
        if depth >= max_depth:
            continue
        
        # Get edges based on direction
        if direction in ("outgoing", "both"):
            if predicates:
                placeholders = ','.join('?' * len(predicates))
                cursor.execute(f"""
                    SELECT id, subject_id, predicate, object_id, object_literal
                    FROM edges
                    WHERE subject_id = ? AND predicate IN ({placeholders})
                """, [current_id] + predicates)
            else:
                cursor.execute("""
                    SELECT id, subject_id, predicate, object_id, object_literal
                    FROM edges
                    WHERE subject_id = ?
                """, (current_id,))
            
            for edge_id, subj_id, pred, obj_id, obj_lit in cursor.fetchall():
                edge_data = {
                    "id": edge_id,
                    "subject_id": subj_id,
                    "predicate": pred,
                    "object_id": obj_id,
                    "object_literal": obj_lit
                }
                subgraph_edges.append(edge_data)
                
                if obj_id and obj_id not in visited_cells:
                    visited_cells.add(obj_id)
                    queue.append((obj_id, depth + 1))
        
        if direction in ("incoming", "both"):
            if predicates:
                placeholders = ','.join('?' * len(predicates))
                cursor.execute(f"""
                    SELECT id, subject_id, predicate, object_id, object_literal
                    FROM edges
                    WHERE object_id = ? AND predicate IN ({placeholders})
                """, [current_id] + predicates)
            else:
                cursor.execute("""
                    SELECT id, subject_id, predicate, object_id, object_literal
                    FROM edges
                    WHERE object_id = ?
                """, (current_id,))
            
            for edge_id, subj_id, pred, obj_id, obj_lit in cursor.fetchall():
                edge_data = {
                    "id": edge_id,
                    "subject_id": subj_id,
                    "predicate": pred,
                    "object_id": obj_id,
                    "object_literal": obj_lit
                }
                subgraph_edges.append(edge_data)
                
                if subj_id not in visited_cells:
                    visited_cells.add(subj_id)
                    queue.append((subj_id, depth + 1))
    
    # Get cell details
    cell_ids = list(visited_cells)
    placeholders = ','.join('?' * len(cell_ids))
    cursor.execute(f"""
        SELECT id, path, differentiation_mode, is_virtual, branch, commit_hash
        FROM relcells
        WHERE id IN ({placeholders})
    """, cell_ids)
    
    cells = []
    for row in cursor.fetchall():
        cells.append({
            "id": row[0],
            "path": row[1],
            "differentiation_mode": row[2],
            "is_virtual": bool(row[3]),
            "branch": row[4],
            "commit_hash": row[5]
        })
    
    return {
        "cells": cells,
        "edges": subgraph_edges
    }


def closure(
    conn: sqlite3.Connection,
    cell_id: int,
    predicate: str,
    direction: str = "outgoing"
) -> Dict[str, Any]:
    """
    Compute transitive closure for a specific predicate.
    
    Args:
        conn: Database connection
        cell_id: Starting cell ID
        predicate: Predicate to follow
        direction: "outgoing" or "incoming"
        
    Returns:
        Dictionary with all reachable cells and edges
    """
    cursor = conn.cursor()
    
    visited = {cell_id}
    edges_list = []
    queue = deque([cell_id])
    
    while queue:
        current_id = queue.popleft()
        
        if direction == "outgoing":
            cursor.execute("""
                SELECT id, subject_id, predicate, object_id
                FROM edges
                WHERE subject_id = ? AND predicate = ? AND object_id IS NOT NULL
            """, (current_id, predicate))
            
            for edge_id, subj, pred, obj in cursor.fetchall():
                edges_list.append({
                    "id": edge_id,
                    "subject_id": subj,
                    "predicate": pred,
                    "object_id": obj
                })
                
                if obj not in visited:
                    visited.add(obj)
                    queue.append(obj)
        else:  # incoming
            cursor.execute("""
                SELECT id, subject_id, predicate, object_id
                FROM edges
                WHERE object_id = ? AND predicate = ?
            """, (current_id, predicate))
            
            for edge_id, subj, pred, obj in cursor.fetchall():
                edges_list.append({
                    "id": edge_id,
                    "subject_id": subj,
                    "predicate": pred,
                    "object_id": obj
                })
                
                if subj not in visited:
                    visited.add(subj)
                    queue.append(subj)
    
    # Get cell details
    cell_ids = list(visited)
    placeholders = ','.join('?' * len(cell_ids))
    cursor.execute(f"""
        SELECT id, path, differentiation_mode, is_virtual
        FROM relcells
        WHERE id IN ({placeholders})
    """, cell_ids)
    
    cells = [
        {
            "id": row[0],
            "path": row[1],
            "differentiation_mode": row[2],
            "is_virtual": bool(row[3])
        }
        for row in cursor.fetchall()
    ]
    
    return {
        "cells": cells,
        "edges": edges_list
    }


def neighbors(
    conn: sqlite3.Connection,
    cell_id: int,
    direction: str = "both",
    predicate_filter: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get immediate neighbors (1-hop) of a cell.
    
    Args:
        conn: Database connection
        cell_id: Target cell ID
        direction: "outgoing", "incoming", or "both"
        predicate_filter: Optional list of predicates
        
    Returns:
        Dictionary with neighboring cells and connecting edges
    """
    return traverse(
        conn, 
        cell_id, 
        predicates=predicate_filter,
        max_depth=1, 
        direction=direction
    )


def query_by_mode(
    conn: sqlite3.Connection,
    differentiation_mode: str
) -> List[Dict[str, Any]]:
    """
    Query all cells by differentiation mode.
    
    Args:
        conn: Database connection
        differentiation_mode: Mode to filter by (git-tree, frontmatter, virtual-synthesis)
        
    Returns:
        List of cells with the specified mode
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, path, differentiation_mode, is_virtual, branch, commit_hash
        FROM relcells
        WHERE differentiation_mode = ?
        ORDER BY path
    """, (differentiation_mode,))
    
    return [
        {
            "id": row[0],
            "path": row[1],
            "differentiation_mode": row[2],
            "is_virtual": bool(row[3]),
            "branch": row[4],
            "commit_hash": row[5]
        }
        for row in cursor.fetchall()
    ]


def find_orphans(
    conn: sqlite3.Connection,
    min_edges: int = 0
) -> List[Dict[str, Any]]:
    """
    Find cells with few or no edges (isolated entities).
    
    Args:
        conn: Database connection
        min_edges: Cells with <= this many edges are considered orphans
        
    Returns:
        List of orphaned cells
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            r.id,
            r.path,
            r.differentiation_mode,
            r.is_virtual,
            COUNT(e.id) as edge_count
        FROM relcells r
        LEFT JOIN edges e ON r.id = e.subject_id OR r.id = e.object_id
        GROUP BY r.id
        HAVING edge_count <= ?
        ORDER BY edge_count, r.path
    """, (min_edges,))
    
    return [
        {
            "id": row[0],
            "path": row[1],
            "differentiation_mode": row[2],
            "is_virtual": bool(row[3]),
            "edge_count": row[4]
        }
        for row in cursor.fetchall()
    ]


def detect_cycles(
    conn: sqlite3.Connection,
    predicate: str,
    max_cycle_length: int = 10
) -> List[List[int]]:
    """
    Detect cycles for a specific predicate using DFS.
    
    Args:
        conn: Database connection
        predicate: Predicate to check for cycles
        max_cycle_length: Maximum cycle length to detect
        
    Returns:
        List of cycles (each cycle is a list of cell IDs)
    """
    cursor = conn.cursor()
    
    # Get all edges for this predicate
    cursor.execute("""
        SELECT subject_id, object_id
        FROM edges
        WHERE predicate = ? AND object_id IS NOT NULL
    """, (predicate,))
    
    # Build adjacency list
    graph = {}
    for subj, obj in cursor.fetchall():
        if subj not in graph:
            graph[subj] = []
        graph[subj].append(obj)
    
    cycles = []
    
    def dfs(node, path, visited_in_path):
        if len(path) > max_cycle_length:
            return
        
        if node in visited_in_path:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:]
            if len(cycle) > 1:  # Ignore self-loops
                cycles.append(cycle)
            return
        
        if node not in graph:
            return
        
        for neighbor in graph[node]:
            dfs(neighbor, path + [neighbor], visited_in_path | {node})
    
    # Start DFS from each node
    for start_node in graph:
        dfs(start_node, [start_node], set())
    
    # Remove duplicate cycles
    unique_cycles = []
    seen = set()
    for cycle in cycles:
        # Normalize cycle (smallest element first)
        min_idx = cycle.index(min(cycle))
        normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
        if normalized not in seen:
            seen.add(normalized)
            unique_cycles.append(list(normalized))
    
    return unique_cycles
