"""
SQLite database schema and operations for RSC.

This module defines the database schema for storing RelCells, Edges,
Provenance, and supporting tables.
"""

import sqlite3
import os
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from contextlib import contextmanager
from datetime import datetime


# Schema version - increment when making schema changes
CURRENT_SCHEMA_VERSION = 1
CURRENT_INGESTOR_VERSION = "0.2.0"


DATABASE_SCHEMA = """
-- === CORE TABLES ===

-- Database state and versioning (single-row table)
CREATE TABLE IF NOT EXISTS db_state (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    schema_version INTEGER NOT NULL,
    ingestor_version TEXT NOT NULL,
    last_ingested_branch TEXT,
    last_ingested_commit TEXT,
    last_ingested_at TIMESTAMP,
    last_ingested_source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- === CORE TABLES ===

-- RelCells: Files as nodes
CREATE TABLE IF NOT EXISTS relcells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    path TEXT NOT NULL,
    
    -- Differentiation metadata (how this cell came into being)
    differentiation_mode TEXT DEFAULT 'git-tree',
    
    -- Cached metadata (denormalized for query performance)
    file_type TEXT,
    mime_type TEXT,
    size_bytes INTEGER,
    checksum TEXT,
    is_virtual BOOLEAN DEFAULT 0,
    
    -- Timestamps
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Composite unique constraint
    UNIQUE(branch, commit_hash, path)
);

CREATE INDEX IF NOT EXISTS idx_relcells_branch ON relcells(branch);
CREATE INDEX IF NOT EXISTS idx_relcells_path ON relcells(path);
CREATE INDEX IF NOT EXISTS idx_relcells_branch_commit ON relcells(branch, commit_hash);
CREATE INDEX IF NOT EXISTS idx_relcells_virtual ON relcells(is_virtual);
CREATE INDEX IF NOT EXISTS idx_relcells_differentiation ON relcells(differentiation_mode);

-- Edges: Relations between RelCells or RelCell and literal
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Triple
    subject_id INTEGER NOT NULL REFERENCES relcells(id) ON DELETE CASCADE,
    predicate TEXT NOT NULL,
    object_id INTEGER REFERENCES relcells(id) ON DELETE CASCADE,
    object_literal TEXT,
    
    -- Provenance
    provenance_id INTEGER NOT NULL REFERENCES provenance(id) ON DELETE CASCADE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (
        (object_id IS NOT NULL AND object_literal IS NULL) OR
        (object_id IS NULL AND object_literal IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_edges_subject ON edges(subject_id);
CREATE INDEX IF NOT EXISTS idx_edges_predicate ON edges(predicate);
CREATE INDEX IF NOT EXISTS idx_edges_object ON edges(object_id);
CREATE INDEX IF NOT EXISTS idx_edges_provenance ON edges(provenance_id);

-- Provenance: Complete audit trail
CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Source location
    branch TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    source_path TEXT NOT NULL,
    
    -- Content span (where in the file)
    span_type TEXT,
    span_start INTEGER,
    span_end INTEGER,
    span_context TEXT,
    
    -- Extraction method
    ingestor TEXT NOT NULL,
    ingestor_version TEXT NOT NULL,
    
    -- Temporal
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_provenance_source ON provenance(source_path);
CREATE INDEX IF NOT EXISTS idx_provenance_commit ON provenance(commit_hash);
CREATE INDEX IF NOT EXISTS idx_provenance_ingestor ON provenance(ingestor);

-- Predicates: Registry of all predicates used
CREATE TABLE IF NOT EXISTS predicates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    
    -- Documentation
    description TEXT,
    domain TEXT,
    range TEXT,
    inverse_of TEXT,
    
    -- Classification
    category TEXT NOT NULL,
    is_core BOOLEAN DEFAULT 0,
    
    -- Metadata
    defined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predicates_category ON predicates(category);
CREATE INDEX IF NOT EXISTS idx_predicates_core ON predicates(is_core);

-- === HELPER TABLES ===

-- Branch relationships (exogenous from Git)
CREATE TABLE IF NOT EXISTS branch_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_branch TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    "commit" TEXT,
    timestamp TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_branch_relations_source ON branch_relations(source_branch);
CREATE INDEX IF NOT EXISTS idx_branch_relations_target ON branch_relations(target_branch);

-- Terms/concepts registry
CREATE TABLE IF NOT EXISTS terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relcell_id INTEGER UNIQUE NOT NULL REFERENCES relcells(id) ON DELETE CASCADE,
    term_id TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL,
    description TEXT,
    aliases TEXT,
    introduced_in INTEGER REFERENCES relcells(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_terms_relcell_id ON terms(relcell_id);
CREATE INDEX IF NOT EXISTS idx_terms_term_id ON terms(term_id);
CREATE INDEX IF NOT EXISTS idx_terms_label ON terms(label);

-- Authors registry
CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relcell_id INTEGER UNIQUE NOT NULL REFERENCES relcells(id) ON DELETE CASCADE,
    author_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    aliases TEXT
);

CREATE INDEX IF NOT EXISTS idx_authors_relcell_id ON authors(relcell_id);
CREATE INDEX IF NOT EXISTS idx_authors_author_id ON authors(author_id);
CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(name);

-- External publications registry
CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relcell_id INTEGER UNIQUE NOT NULL REFERENCES relcells(id) ON DELETE CASCADE,
    citation_key TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    authors_json TEXT,
    year INTEGER,
    venue TEXT,
    doi TEXT,
    url TEXT,
    extra_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_publications_relcell_id ON publications(relcell_id);
CREATE INDEX IF NOT EXISTS idx_publications_citation_key ON publications(citation_key);

-- Document metadata cache (denormalized for performance)
CREATE TABLE IF NOT EXISTS document_metadata (
    relcell_id INTEGER PRIMARY KEY REFERENCES relcells(id) ON DELETE CASCADE,
    doc_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    status TEXT,
    document_type TEXT,
    authors TEXT,
    date_created TEXT,
    date_modified TEXT,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_document_metadata_doc_id ON document_metadata(doc_id);
CREATE INDEX IF NOT EXISTS idx_document_metadata_status ON document_metadata(status);
CREATE INDEX IF NOT EXISTS idx_document_metadata_type ON document_metadata(document_type);

-- === VIEWS FOR COMMON QUERIES ===

-- View: All internal citations
CREATE VIEW IF NOT EXISTS v_internal_citations AS
SELECT 
    s.path as source_path,
    sd.title as source_title,
    e.predicate,
    t.path as target_path,
    td.title as target_title,
    p.source_path as provenance_source,
    p.span_type,
    p.span_start,
    p.span_end
FROM edges e
JOIN relcells s ON e.subject_id = s.id
JOIN relcells t ON e.object_id = t.id
LEFT JOIN document_metadata sd ON s.id = sd.relcell_id
LEFT JOIN document_metadata td ON t.id = td.relcell_id
LEFT JOIN provenance p ON e.provenance_id = p.id
WHERE e.predicate IN ('cites_internal', 'cited_by', 'builds_on');

-- View: Document catalog
CREATE VIEW IF NOT EXISTS v_document_catalog AS
SELECT 
    r.branch,
    r.commit_hash,
    r.path,
    m.doc_id,
    m.title,
    m.status,
    m.document_type,
    m.authors,
    m.date_created,
    m.date_modified,
    r.size_bytes,
    r.ingested_at
FROM relcells r
JOIN document_metadata m ON r.id = m.relcell_id
WHERE r.is_virtual = 0;

-- View: Term definitions
CREATE VIEW IF NOT EXISTS v_term_definitions AS
SELECT 
    t.term_id,
    t.label,
    t.description,
    t.aliases,
    rc.path as virtual_path,
    r.path as introduced_in_path,
    m.title as introduced_in_title
FROM terms t
JOIN relcells rc ON t.relcell_id = rc.id
LEFT JOIN relcells r ON t.introduced_in = r.id
LEFT JOIN document_metadata m ON r.id = m.relcell_id;

-- View: Author directory
CREATE VIEW IF NOT EXISTS v_authors AS
SELECT 
    a.author_id,
    a.name,
    a.aliases,
    rc.path as virtual_path,
    rc.branch,
    rc.commit_hash
FROM authors a
JOIN relcells rc ON a.relcell_id = rc.id;

-- View: Publication catalog
CREATE VIEW IF NOT EXISTS v_publications AS
SELECT 
    p.citation_key,
    p.title,
    p.authors_json,
    p.year,
    p.venue,
    p.doi,
    p.url,
    rc.path as virtual_path
FROM publications p
JOIN relcells rc ON p.relcell_id = rc.id;
"""


class Database:
    """
    RSC database interface.
    
    Manages SQLite connection and provides methods for creating,
    querying, and maintaining the RSC graph database.
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
    
    def connect(self):
        """Open database connection."""
        self.connection = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.connection.row_factory = sqlite3.Row
        
        # Enable foreign key constraints
        self.connection.execute("PRAGMA foreign_keys = ON")
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()
    
    def initialize_schema(self):
        """Create all tables and indexes."""
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        self.connection.executescript(DATABASE_SCHEMA)
        self.connection.commit()
        
        # Initialize db_state if empty
        cursor = self.connection.execute("SELECT COUNT(*) FROM db_state")
        if cursor.fetchone()[0] == 0:
            self.connection.execute("""
                INSERT INTO db_state (id, schema_version, ingestor_version)
                VALUES (1, ?, ?)
            """, (CURRENT_SCHEMA_VERSION, CURRENT_INGESTOR_VERSION))
            self.connection.commit()
        
        # Set PRAGMA user_version
        self.connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
        self.connection.commit()
    
    def ensure_schema_version(self):
        """Check schema version and raise if mismatch."""
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        # Check PRAGMA user_version
        cursor = self.connection.execute("PRAGMA user_version")
        pragma_version = cursor.fetchone()[0]
        
        # Check db_state.schema_version
        cursor = self.connection.execute("SELECT schema_version FROM db_state WHERE id = 1")
        row = cursor.fetchone()
        
        if not row:
            raise RuntimeError(
                "Database missing db_state row. Please run initialize_schema() or "
                "restore from backup."
            )
        
        db_version = row[0]
        
        if pragma_version != CURRENT_SCHEMA_VERSION or db_version != CURRENT_SCHEMA_VERSION:
            raise RuntimeError(
                f"Schema version mismatch! "
                f"Current code expects v{CURRENT_SCHEMA_VERSION}, "
                f"but database has PRAGMA={pragma_version}, db_state={db_version}. "
                f"Please run database migration or re-initialize."
            )
    
    def record_ingestion_state(
        self,
        branch: str,
        commit_hash: str,
        source: str,
        ingestor_version: Optional[str] = None
    ):
        """Record ingestion metadata after successful ingestion."""
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        version = ingestor_version or CURRENT_INGESTOR_VERSION
        
        with self.transaction() as cursor:
            cursor.execute("""
                UPDATE db_state
                SET ingestor_version = ?,
                    last_ingested_branch = ?,
                    last_ingested_commit = ?,
                    last_ingested_at = CURRENT_TIMESTAMP,
                    last_ingested_source = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (version, branch, commit_hash, source))
    
    def insert_relcell(
        self,
        branch: str,
        commit_hash: str,
        path: str,
        file_type: Optional[str] = None,
        mime_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
        checksum: Optional[str] = None,
        is_virtual: bool = False
    ) -> int:
        """
        Insert a RelCell into the database.
        
        Returns:
            The ID of the inserted RelCell
        """
        with self.transaction() as cursor:
            cursor.execute("""
                INSERT INTO relcells (
                    branch, commit_hash, path, file_type, mime_type,
                    size_bytes, checksum, is_virtual
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (branch, commit_hash, path, file_type, mime_type,
                  size_bytes, checksum, is_virtual))
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("Failed to insert RelCell")
            return row_id
    
    def get_relcell_id(self, branch: str, commit_hash: str, path: str) -> Optional[int]:
        """Get RelCell ID by (branch, commit_hash, path)."""
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        cursor = self.connection.execute("""
            SELECT id FROM relcells
            WHERE branch = ? AND commit_hash = ? AND path = ?
        """, (branch, commit_hash, path))
        
        row = cursor.fetchone()
        return row[0] if row else None
    
    def insert_edge(
        self,
        subject_id: int,
        predicate: str,
        object_id: Optional[int] = None,
        object_literal: Optional[str] = None,
        provenance_id: Optional[int] = None
    ) -> int:
        """
        Insert an Edge into the database.
        
        Returns:
            The ID of the inserted Edge
        """
        with self.transaction() as cursor:
            cursor.execute("""
                INSERT INTO edges (
                    subject_id, predicate, object_id, object_literal, provenance_id
                ) VALUES (?, ?, ?, ?, ?)
            """, (subject_id, predicate, object_id, object_literal, provenance_id))
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("Failed to insert Edge")
            return row_id
    
    def insert_provenance(
        self,
        branch: str,
        commit_hash: str,
        source_path: str,
        span_type: Optional[str] = None,
        span_start: Optional[int] = None,
        span_end: Optional[int] = None,
        span_context: Optional[str] = None,
        ingestor: str = "unknown",
        ingestor_version: str = "0.1.0"
    ) -> int:
        """
        Insert Provenance into the database.
        
        Returns:
            The ID of the inserted Provenance
        """
        with self.transaction() as cursor:
            cursor.execute("""
                INSERT INTO provenance (
                    branch, commit_hash, source_path,
                    span_type, span_start, span_end, span_context,
                    ingestor, ingestor_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (branch, commit_hash, source_path, span_type, span_start,
                  span_end, span_context, ingestor, ingestor_version))
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("Failed to insert Provenance")
            return row_id
    
    def register_predicate(
        self,
        name: str,
        description: str,
        domain: str,
        range: str,
        category: str,
        inverse_of: Optional[str] = None,
        is_core: bool = False
    ):
        """Register a predicate in the database."""
        with self.transaction() as cursor:
            cursor.execute("""
                INSERT OR IGNORE INTO predicates (
                    name, description, domain, range, category, inverse_of, is_core
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, description, domain, range, category, inverse_of, is_core))
    
    def perform_backup(self, backup_dir: Optional[Path] = None, max_backups: int = 5) -> Path:
        """
        Create a timestamped backup of the database.
        
        Args:
            backup_dir: Directory for backups (default: data/databases/backups/)
            max_backups: Maximum number of backups to keep (default: 5)
        
        Returns:
            Path to the created backup file
        """
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        # Default backup directory
        if backup_dir is None:
            backup_dir = self.db_path.parent / "backups"
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = backup_dir / f"rsc-{timestamp}.sqlite"
        
        # Perform WAL checkpoint before backup
        self.connection.execute("PRAGMA wal_checkpoint(FULL)")
        
        # Use SQLite's backup API for atomic copy
        backup_conn = sqlite3.connect(backup_path)
        try:
            self.connection.backup(backup_conn)
        finally:
            backup_conn.close()
        
        # Rotate old backups
        self._rotate_backups(backup_dir, max_backups)
        
        return backup_path
    
    def _rotate_backups(self, backup_dir: Path, max_backups: int):
        """Keep only the most recent N backups."""
        backups = sorted(backup_dir.glob("rsc-*.sqlite"), reverse=True)
        
        for old_backup in backups[max_backups:]:
            old_backup.unlink()
    
    @staticmethod
    def list_backups(backup_dir: Optional[Path] = None) -> List[Tuple[Path, datetime]]:
        """
        List available backups with timestamps.
        
        Returns:
            List of (path, timestamp) tuples, sorted newest first
        """
        if backup_dir is None:
            backup_dir = Path("data/databases/backups")
        
        if not backup_dir.exists():
            return []
        
        backups = []
        for backup_file in backup_dir.glob("rsc-*.sqlite"):
            # Parse timestamp from filename
            try:
                timestamp_str = backup_file.stem.replace("rsc-", "")
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S")
                backups.append((backup_file, timestamp))
            except ValueError:
                continue
        
        return sorted(backups, key=lambda x: x[1], reverse=True)
    
    def restore_backup(self, backup_path: Path):
        """
        Restore database from a backup file.
        
        Args:
            backup_path: Path to backup file to restore
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Verify backup is valid SQLite database
        try:
            test_conn = sqlite3.connect(backup_path)
            cursor = test_conn.execute("SELECT schema_version FROM db_state WHERE id = 1")
            backup_version = cursor.fetchone()
            test_conn.close()
            
            if not backup_version:
                raise RuntimeError("Backup missing db_state table")
                
            if backup_version[0] != CURRENT_SCHEMA_VERSION:
                raise RuntimeError(
                    f"Backup schema version ({backup_version[0]}) "
                    f"doesn't match current version ({CURRENT_SCHEMA_VERSION})"
                )
        except sqlite3.Error as e:
            raise RuntimeError(f"Invalid backup file: {e}")
        
        # Close current connection
        was_connected = self.connection is not None
        if was_connected:
            self.disconnect()
        
        # Replace database file atomically
        temp_path = self.db_path.with_suffix(".tmp")
        shutil.copy2(backup_path, temp_path)
        temp_path.replace(self.db_path)
        
        # Reconnect if we were connected before
        if was_connected:
            self.connect()
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        stats = {}
        
        cursor = self.connection.execute("SELECT COUNT(*) FROM relcells")
        stats['total_relcells'] = cursor.fetchone()[0]
        
        cursor = self.connection.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 0")
        stats['file_relcells'] = cursor.fetchone()[0]
        
        cursor = self.connection.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 1")
        stats['virtual_relcells'] = cursor.fetchone()[0]
        
        cursor = self.connection.execute("SELECT COUNT(*) FROM edges")
        stats['total_edges'] = cursor.fetchone()[0]
        
        cursor = self.connection.execute("SELECT COUNT(DISTINCT predicate) FROM edges")
        stats['unique_predicates'] = cursor.fetchone()[0]
        
        cursor = self.connection.execute("SELECT COUNT(*) FROM terms")
        stats['total_terms'] = cursor.fetchone()[0]
        
        cursor = self.connection.execute("SELECT COUNT(*) FROM document_metadata")
        stats['documents_with_metadata'] = cursor.fetchone()[0]
        
        return stats


def create_database(db_path: Path) -> Database:
    """
    Create and initialize a new RSC database.
    
    Args:
        db_path: Path where database should be created
    
    Returns:
        Connected and initialized Database instance
    """
    db = Database(db_path)
    db.connect()
    db.initialize_schema()
    
    # Register core predicates
    from .predicates import CORE_PREDICATES
    for predicate in CORE_PREDICATES.values():
        db.register_predicate(
            name=predicate.name,
            description=predicate.description,
            domain=predicate.domain,
            range=predicate.range,
            category=predicate.category.value,
            inverse_of=predicate.inverse_of,
            is_core=predicate.is_core
        )
    
    return db


DB_PATH: Optional[str] = None


def init_database(db_path: Optional[str] = None):
    """Initialize the database using the Database class method."""
    global DB_PATH
    if db_path:
        DB_PATH = db_path
    else:
        if not DB_PATH:
            DB_PATH = "rsc.db"
    
    db = Database(Path(DB_PATH))
    db.connect()
    db.initialize_schema()
    db.disconnect()


def get_db_connection() -> sqlite3.Connection:
    """
    Get a connection to the database.
    
    Checks for RSC_DB_PATH environment variable (for testing and config),
    then falls back to global DB_PATH, then defaults to data/databases/rsc.db.
    """
    global DB_PATH
    
    # Check for database path in environment (pytest and config use this)
    env_path = os.environ.get("RSC_DB_PATH")
    if env_path:
        return sqlite3.connect(env_path)
    
    # Fall back to global DB_PATH or default
    if not DB_PATH:
        DB_PATH = "data/databases/rsc.db"
    
    return sqlite3.connect(DB_PATH)


def dict_factory(cursor, row):
    """Convert SQL row to dictionary."""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}
