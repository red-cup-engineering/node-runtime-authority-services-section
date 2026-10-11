"""
Tests for the Markdown ingestor.
"""

import pytest
from pathlib import Path
import tempfile
import sqlite3

from rsc.ingestor import ingest_markdown_file, IngestionError
from rsc.database import init_database, get_db_connection


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    init_database(db_path)
    
    import rsc.database as db_module
    original_db = db_module.DB_PATH
    db_module.DB_PATH = db_path
    
    yield db_path
    
    db_module.DB_PATH = original_db
    
    Path(db_path).unlink(missing_ok=True)


def test_ingest_simple_document(temp_db):
    """Test ingesting a simple document with minimal frontmatter."""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""+++
id = "test-doc"
title = "Test Document"
authors = ["Test Author"]
+++

# Test Content

This is a test document.
""")
        doc_path = Path(f.name)
    
    try:
        result = ingest_markdown_file(
            doc_path,
            branch="test-branch",
            commit_hash="abc123"
        )
        
        assert result.document_relcell_id is not None
        assert len(result.author_relcells) == 1
        assert result.edges_created > 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 0")
        doc_count = cursor.fetchone()[0]
        assert doc_count == 1
        
        cursor.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 1 AND virtual_type = 'author'")
        author_count = cursor.fetchone()[0]
        assert author_count == 1
        
        cursor.execute("SELECT COUNT(*) FROM edges WHERE predicate = 'author'")
        author_edge_count = cursor.fetchone()[0]
        assert author_edge_count == 1
        
        conn.close()
        
    finally:
        doc_path.unlink(missing_ok=True)


def test_ingest_document_with_terms(temp_db):
    """Test ingesting a document with term definitions."""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""+++
id = "test-terms"
title = "Test Terms"

[[defines]]
id = "test-term"
label = "Test Term"
description = "A test term definition"
+++

# Content

Test content.
""")
        doc_path = Path(f.name)
    
    try:
        result = ingest_markdown_file(doc_path, branch="main", commit_hash="def456")
        
        assert result.document_relcell_id is not None
        assert len(result.term_relcells) == 1
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM relcells WHERE virtual_type = 'term'")
        term_count = cursor.fetchone()[0]
        assert term_count == 1
        
        cursor.execute("SELECT COUNT(*) FROM edges WHERE predicate = 'defines'")
        defines_count = cursor.fetchone()[0]
        assert defines_count == 1
        
        cursor.execute("""
            SELECT target_literal FROM edges 
            WHERE predicate = 'has_label' 
            AND source_id IN (SELECT id FROM relcells WHERE virtual_type = 'term')
        """)
        label = cursor.fetchone()[0]
        assert label == "Test Term"
        
        conn.close()
        
    finally:
        doc_path.unlink(missing_ok=True)


def test_ingest_nonexistent_file(temp_db):
    """Test that ingesting a nonexistent file raises an error."""
    
    with pytest.raises(IngestionError, match="File not found"):
        ingest_markdown_file(Path("/nonexistent/file.md"))


def test_ingest_file_without_frontmatter(temp_db):
    """Test that ingesting a file without frontmatter raises an error."""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Just a heading\n\nNo frontmatter here.")
        doc_path = Path(f.name)
    
    try:
        with pytest.raises(IngestionError, match="No frontmatter found"):
            ingest_markdown_file(doc_path)
    finally:
        doc_path.unlink(missing_ok=True)


def test_ingest_proposing_relationing(temp_db):
    """Test ingesting the actual Proposing Relationing document."""
    
    doc_path = Path("txt/scientific-texts/relations/proposing-relationing.md")
    
    if not doc_path.exists():
        pytest.skip("Proposing Relationing document not found")
    
    result = ingest_markdown_file(
        doc_path,
        branch="refactor/2025-11",
        commit_hash="test-commit"
    )
    
    assert result.document_relcell_id is not None
    assert len(result.term_relcells) == 16
    assert len(result.author_relcells) == 1
    assert result.edges_created > 50
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM relcells WHERE virtual_type = 'term'")
    term_count = cursor.fetchone()[0]
    assert term_count == 16
    
    cursor.execute("SELECT virtual_id FROM relcells WHERE virtual_type = 'term' ORDER BY virtual_id")
    term_ids = [row[0] for row in cursor.fetchall()]
    
    assert "virtual:term.differentiation" in term_ids
    assert "virtual:term.recognition" in term_ids
    assert "virtual:term.relationing" in term_ids
    
    conn.close()
