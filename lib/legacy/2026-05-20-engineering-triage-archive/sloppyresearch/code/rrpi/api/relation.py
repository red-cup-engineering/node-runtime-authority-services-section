"""
Relation API endpoints.

Relation: Edges connecting recognized cells in the graph.
These endpoints expose various relational structures: citations,
authorship, Git history, and other predicates.

Theoretical Foundation:
- Relations are directed edges with typed predicates
- Citations are relations between documents (internal) or to external publications
- Authorship relations connect agents (authors) to produced content (documents)
- Git relations track provenance and history
"""

from fastapi import APIRouter
from typing import List, Dict, Any

from rrpi.database import get_db_connection
from rrpi.api.utils import dict_factory
from rrpi.api.relationing_metadata import relationing_cell

router = APIRouter(prefix="/api/relation", tags=["relation"])


@router.get("/citations")
@relationing_cell(
    instantiates_terms=["relation", "reference"],
    differentiation_modes=["frontmatter"],
    predicates=["cites_internal", "cites_external", "cited_by", "depends_on"],
    narrative="Enumerates all citation relations. Internal citations are edges between documents; external citations point to publications beyond the repository.",
    examples=["Proposing Relationing cites Vine Deloria Jr. (external)", "Research note cites Proposing Relationing (internal)"]
)
async def list_citations() -> List[Dict[str, Any]]:
    """
    List all citation relations (internal and external).
    
    Relationing Semantics:
    - Relation: Citations are directed edges between documents
    - Reference: Documents acknowledge and build upon prior work
    - Network: Citations form a dependency graph of ideas
    """
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


@router.get("/contributions")
@relationing_cell(
    instantiates_terms=["relation", "authorship", "agency"],
    differentiation_modes=["virtual-synthesis"],
    predicates=["commit_authored_by", "has_name"],
    narrative="Enumerates authorship relations from Git history. Shows which agents (Git authors) have contributed commits, revealing the collaborative production of the repository.",
    examples=["emsenn: 127 commits", "collaborator: 3 commits"]
)
async def get_author_contributions() -> List[Dict[str, Any]]:
    """
    Get author contribution metrics from Git history.
    
    Relationing Semantics:
    - Relation: Maps authors to their produced commits
    - Agency: Authors are agents who effect change in the repository
    - Quantification: Contribution counts measure productive activity
    """
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
