"""
Markdown document ingestor for RSC system.

Ingests Markdown files with TOML frontmatter into the RelCell database,
creating document RelCells, virtual cells for terms/authors, and edges
representing relationships.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import sqlite3

from rrpi.frontmatter_parser import parse_markdown_file
from rrpi.database import get_db_connection
from rrpi.virtual_cells import (
    create_virtual_term_id,
    create_virtual_author_id,
    create_virtual_publication_id
)
from rrpi.predicates import Predicate


class IngestionError(Exception):
    """Raised when ingestion fails."""
    pass


class IngestionResult:
    """Result of ingesting a document."""
    
    def __init__(self):
        self.document_relcell_id: Optional[int] = None
        self.term_relcells: list[int] = []
        self.author_relcells: list[int] = []
        self.edges_created: int = 0
        self.errors: list[str] = []
    
    def __str__(self):
        return (
            f"IngestionResult(\n"
            f"  document_relcell_id={self.document_relcell_id},\n"
            f"  terms={len(self.term_relcells)},\n"
            f"  authors={len(self.author_relcells)},\n"
            f"  edges={self.edges_created}\n"
            f")"
        )


def ingest_markdown_file(
    file_path: Path,
    branch: str = "refactor/2025-11",
    commit_hash: Optional[str] = None,
    repo_root: Optional[Path] = None
) -> IngestionResult:
    """
    Ingest a Markdown file into the RSC database.
    
    Creates:
    1. Document RelCell (identified by branch, commit, path)
    2. Virtual RelCells for terms defined in the document
    3. Virtual RelCells for authors
    4. Edges connecting document to terms, authors, citations
    
    Args:
        file_path: Path to the Markdown file
        branch: Git branch name
        commit_hash: Git commit hash (optional, uses "HEAD" if None)
        repo_root: Repository root path for relative path calculation
    
    Returns:
        IngestionResult with details of what was created
    
    Raises:
        IngestionError: If ingestion fails
    """
    result = IngestionResult()
    
    if not file_path.exists():
        raise IngestionError(f"File not found: {file_path}")
    
    if commit_hash is None:
        commit_hash = "HEAD"
    
    if repo_root is None:
        repo_root = Path.cwd()
    
    try:
        relative_path = file_path.relative_to(repo_root)
    except ValueError:
        relative_path = file_path
    
    relative_path_str = str(relative_path)
    
    metadata, body = parse_markdown_file(file_path)
    
    if metadata is None:
        raise IngestionError(f"No frontmatter found in {file_path}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        provenance_id = _insert_provenance(
            cursor,
            branch=branch,
            commit_hash=commit_hash,
            source_path=relative_path_str
        )
        
        doc_relcell_id = _insert_relcell(
            cursor,
            branch=branch,
            commit_hash=commit_hash,
            path=relative_path_str,
            is_virtual=False
        )
        
        result.document_relcell_id = doc_relcell_id
        doc_id = doc_relcell_id
        
        _create_document_metadata_edges(cursor, doc_id, metadata, provenance_id, result)
        _create_term_virtual_cells(cursor, doc_id, metadata, branch, commit_hash, provenance_id, result)
        _create_author_virtual_cells(cursor, doc_id, metadata, branch, commit_hash, provenance_id, result)
        _create_citation_edges(cursor, doc_id, metadata, branch, commit_hash, provenance_id, result)
        
        conn.commit()
        
        return result
        
    except Exception as e:
        conn.rollback()
        raise IngestionError(f"Failed to ingest {file_path}: {e}") from e
    finally:
        conn.close()


def _insert_relcell(cursor: sqlite3.Cursor, branch: str, commit_hash: str, path: str, is_virtual: bool = False) -> int:
    """
    Insert a RelCell or return existing ID if it already exists.
    
    For virtual cells, this prevents collision errors when multiple documents
    share the same author or term.
    """
    cursor.execute(
        'SELECT id FROM relcells WHERE branch = ? AND commit_hash = ? AND path = ?',
        (branch, commit_hash, path)
    )
    existing = cursor.fetchone()
    if existing:
        return existing[0]
    
    cursor.execute("""
        INSERT INTO relcells (branch, commit_hash, path, differentiation_mode, is_virtual)
        VALUES (?, ?, ?, ?, ?)
    """, (branch, commit_hash, path, 'frontmatter', 1 if is_virtual else 0))
    row_id = cursor.lastrowid
    if row_id is None:
        raise IngestionError("Failed to insert RelCell")
    return row_id


def _insert_provenance(cursor: sqlite3.Cursor, branch: str, commit_hash: str, source_path: str) -> int:
    """Insert provenance record and return its ID."""
    cursor.execute("""
        INSERT INTO provenance (
            branch, commit_hash, source_path, ingestor, ingestor_version, extracted_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (branch, commit_hash, source_path, "markdown_ingestor", "1.0", datetime.utcnow().isoformat()))
    row_id = cursor.lastrowid
    if row_id is None:
        raise IngestionError("Failed to insert provenance")
    return row_id


def _insert_edge(
    cursor: sqlite3.Cursor,
    subject_id: int,
    predicate: str,
    provenance_id: int,
    object_id: Optional[int] = None,
    object_literal: Optional[str] = None
) -> int:
    """Insert an edge and return its ID."""
    cursor.execute("""
        INSERT INTO edges (subject_id, predicate, object_id, object_literal, provenance_id)
        VALUES (?, ?, ?, ?, ?)
    """, (subject_id, predicate, object_id, object_literal, provenance_id))
    row_id = cursor.lastrowid
    if row_id is None:
        raise IngestionError("Failed to insert edge")
    return row_id


def _create_document_metadata_edges(
    cursor: sqlite3.Cursor,
    doc_relcell_id: int,
    metadata,
    provenance_id: int,
    result: IngestionResult
):
    """Create edges for document metadata (title, status, type, etc.)."""
    
    # Insert into document_metadata table for efficient querying
    authors_json = ",".join(metadata.authors) if metadata.authors else None
    cursor.execute("""
        INSERT OR REPLACE INTO document_metadata (
            relcell_id, doc_id, title, status, document_type,
            authors, date_created, date_modified, last_synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        doc_relcell_id,
        metadata.id,
        metadata.title,
        metadata.status,
        metadata.document_type,
        authors_json,
        metadata.date_created,
        metadata.date_modified
    ))
    
    # Create edges for graph traversal
    if metadata.title:
        _insert_edge(cursor, doc_relcell_id, Predicate.HAS_TITLE.value, provenance_id, object_literal=metadata.title)
        result.edges_created += 1
    
    if metadata.status:
        _insert_edge(cursor, doc_relcell_id, Predicate.HAS_STATUS.value, provenance_id, object_literal=metadata.status)
        result.edges_created += 1
    
    if metadata.document_type:
        _insert_edge(cursor, doc_relcell_id, Predicate.HAS_DOCUMENT_TYPE.value, provenance_id, object_literal=metadata.document_type)
        result.edges_created += 1
    
    if metadata.date_created:
        _insert_edge(cursor, doc_relcell_id, Predicate.CREATED_ON.value, provenance_id, object_literal=metadata.date_created)
        result.edges_created += 1
    
    if metadata.date_modified:
        _insert_edge(cursor, doc_relcell_id, Predicate.MODIFIED_ON.value, provenance_id, object_literal=metadata.date_modified)
        result.edges_created += 1
    
    for topic in metadata.topics:
        _insert_edge(cursor, doc_relcell_id, Predicate.HAS_TOPIC.value, provenance_id, object_literal=topic)
        result.edges_created += 1
    
    for keyword in metadata.keywords:
        _insert_edge(cursor, doc_relcell_id, Predicate.HAS_KEYWORD.value, provenance_id, object_literal=keyword)
        result.edges_created += 1


def _create_term_virtual_cells(
    cursor: sqlite3.Cursor,
    doc_relcell_id: int,
    metadata,
    branch: str,
    commit_hash: str,
    provenance_id: int,
    result: IngestionResult
):
    """Create virtual RelCells for terms defined in the document."""
    
    for term_def in metadata.defines:
        virtual_id = create_virtual_term_id(term_def.id)
        
        term_relcell_id = _insert_relcell(
            cursor,
            branch=branch,
            commit_hash=commit_hash,
            path=virtual_id,
            is_virtual=True
        )
        result.term_relcells.append(term_relcell_id)
        
        # Insert into terms table
        aliases_json = ",".join(term_def.aliases) if term_def.aliases else None
        cursor.execute("""
            INSERT OR IGNORE INTO terms (
                relcell_id, term_id, label, description, aliases, introduced_in
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (term_relcell_id, term_def.id, term_def.label, term_def.description, aliases_json, doc_relcell_id))
        
        _insert_edge(cursor, doc_relcell_id, Predicate.DEFINES.value, provenance_id, object_id=term_relcell_id)
        result.edges_created += 1
        
        _insert_edge(cursor, term_relcell_id, Predicate.HAS_LABEL.value, provenance_id, object_literal=term_def.label)
        result.edges_created += 1
        
        if term_def.description:
            _insert_edge(cursor, term_relcell_id, Predicate.HAS_DESCRIPTION.value, provenance_id, object_literal=term_def.description)
            result.edges_created += 1
        
        for alias in term_def.aliases:
            _insert_edge(cursor, term_relcell_id, Predicate.HAS_ALIAS.value, provenance_id, object_literal=alias)
            result.edges_created += 1


def _create_author_virtual_cells(
    cursor: sqlite3.Cursor,
    doc_relcell_id: int,
    metadata,
    branch: str,
    commit_hash: str,
    provenance_id: int,
    result: IngestionResult
):
    """Create virtual RelCells for authors."""
    
    for author_name in metadata.authors:
        virtual_id = create_virtual_author_id(author_name)
        
        author_relcell_id = _insert_relcell(
            cursor,
            branch=branch,
            commit_hash=commit_hash,
            path=virtual_id,
            is_virtual=True
        )
        result.author_relcells.append(author_relcell_id)
        
        # Insert into authors table
        author_id = virtual_id.replace("virtual:author.", "")
        cursor.execute("""
            INSERT OR IGNORE INTO authors (
                relcell_id, author_id, name, aliases
            ) VALUES (?, ?, ?, ?)
        """, (author_relcell_id, author_id, author_name, None))
        
        _insert_edge(cursor, doc_relcell_id, Predicate.AUTHOR.value, provenance_id, object_id=author_relcell_id)
        result.edges_created += 1
        
        _insert_edge(cursor, author_relcell_id, Predicate.HAS_NAME.value, provenance_id, object_literal=author_name)
        result.edges_created += 1


def _create_citation_edges(
    cursor: sqlite3.Cursor,
    doc_relcell_id: int,
    metadata,
    branch: str,
    commit_hash: str,
    provenance_id: int,
    result: IngestionResult
):
    """Create edges for citations (internal and external)."""
    
    for cited_doc_id in metadata.cites_internal:
        _insert_edge(cursor, doc_relcell_id, Predicate.CITES_INTERNAL.value, provenance_id, object_literal=cited_doc_id)
        result.edges_created += 1
    
    for ext_citation in metadata.cites_external:
        citation_virtual_id = create_virtual_publication_id(ext_citation.key)
        
        pub_relcell_id = _insert_relcell(
            cursor,
            branch=branch,
            commit_hash=commit_hash,
            path=citation_virtual_id,
            is_virtual=True
        )
        
        _insert_edge(cursor, doc_relcell_id, Predicate.CITES_EXTERNAL.value, provenance_id, object_id=pub_relcell_id)
        result.edges_created += 1
        
        if ext_citation.title:
            _insert_edge(cursor, pub_relcell_id, Predicate.HAS_TITLE.value, provenance_id, object_literal=ext_citation.title)
            result.edges_created += 1
        
        for author in ext_citation.authors:
            _insert_edge(cursor, pub_relcell_id, Predicate.AUTHOR.value, provenance_id, object_literal=author)
            result.edges_created += 1
