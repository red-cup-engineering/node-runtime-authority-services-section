"""
Git metadata extraction module.

Extracts comprehensive Git metadata from a repository to create rich edge networks:
- File tracking (all files in repository)
- Commit history (authors, timestamps, messages, parents)
- Branch relationships
- Tags and releases
- File modifications, creations, deletions, renames
"""

import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

import git
from git import Repo, Commit, Tree, Blob

from .models import RelCell, Edge, Provenance
from .database import get_db_connection, dict_factory
from .predicates import Predicate


def get_or_create_virtual_cell(conn, cursor, virtual_path: str, cell_type: str) -> int:
    """
    Get or create a virtual cell and return its ID.
    
    Args:
        conn: Database connection
        cursor: Database cursor
        virtual_path: Full virtual path (e.g., "virtual:commit:abc123")
        cell_type: Type of virtual cell (e.g., "commit", "git-author")
        
    Returns:
        RelCell ID
    """
    # Check if exists
    cursor.execute("""
        SELECT id FROM relcells WHERE path = ? AND is_virtual = 1
    """, (virtual_path,))
    
    existing = cursor.fetchone()
    if existing:
        return existing[0]
    
    # Create new virtual cell
    cursor.execute("""
        INSERT INTO relcells (
            branch, commit_hash, path, file_type, differentiation_mode, 
            is_virtual, ingested_at
        ) VALUES (?, ?, ?, ?, 'virtual-synthesis', 1, datetime('now'))
    """, ("virtual", "virtual", virtual_path, cell_type))
    
    return cursor.lastrowid


class GitExtractor:
    """Extract Git metadata and create RelCells/edges."""
    
    def __init__(self, repo_path: str = "."):
        """
        Initialize Git extractor.
        
        Args:
            repo_path: Path to Git repository (default: current directory)
        """
        self.repo_path = Path(repo_path)
        self.repo = Repo(self.repo_path)
        self.db_path = self.repo_path / "rsc.db"
        
        # Initialize mimetypes
        mimetypes.init()
        
        # Cache current branch and commit for easy access
        try:
            self.current_branch = self.get_current_branch()
            self.current_commit = self.get_current_commit()
        except Exception:
            # If detached HEAD or other Git issue, use defaults
            self.current_branch = "unknown"
            self.current_commit = "unknown"
    
    def get_current_branch(self) -> str:
        """Get current branch name."""
        return self.repo.active_branch.name
    
    def get_current_commit(self) -> str:
        """Get current commit hash."""
        return self.repo.head.commit.hexsha
    
    def compute_file_checksum(self, file_path: Path) -> str:
        """
        Compute SHA-256 checksum of file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex string of checksum
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return ""
    
    def get_mime_type(self, file_path: Path) -> str:
        """
        Get MIME type of file.
        
        Args:
            file_path: Path to file
            
        Returns:
            MIME type string
        """
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"
    
    def ingest_repository_files(
        self,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
        skip_patterns: Optional[List[str]] = None,
        respect_gitignore: bool = True
    ) -> Tuple[int, int]:
        """
        Ingest all files from repository at current state.
        
        Args:
            branch: Branch name (defaults to current branch)
            commit_hash: Commit hash (defaults to current commit)
            skip_patterns: Patterns to skip (e.g., ['.git', '__pycache__', '*.pyc'])
            respect_gitignore: Skip files ignored by .gitignore (default: True)
            
        Returns:
            Tuple of (files_ingested, edges_created)
        """
        if branch is None:
            branch = self.get_current_branch()
        if commit_hash is None:
            commit_hash = self.get_current_commit()
        if skip_patterns is None:
            skip_patterns = ['.git', '__pycache__', '*.pyc', '*.pyo', 
                           'node_modules', '.pytest_cache', 'rsc.db']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        files_ingested = 0
        edges_created = 0
        files_skipped = 0
        
        # Create provenance record
        provenance_id = self._create_provenance(
            conn, branch, commit_hash, "repository", 
            "git_extractor", "1.0"
        )
        
        # Walk repository tree
        for file_path in self.repo_path.rglob('*'):
            # Skip directories and excluded patterns
            if file_path.is_dir():
                continue
            
            relative_path = file_path.relative_to(self.repo_path)
            relative_str = str(relative_path)
            
            # Skip patterns
            if any(self._matches_pattern(relative_str, pattern) 
                   for pattern in skip_patterns):
                files_skipped += 1
                continue
            
            # Respect .gitignore
            if respect_gitignore and self._is_ignored(relative_str):
                files_skipped += 1
                continue
            
            # Create RelCell for file
            relcell_id = self._create_file_relcell(
                conn, cursor, branch, commit_hash, 
                str(relative_path), file_path, provenance_id
            )
            
            if relcell_id:
                files_ingested += 1
                
                # Create edges for file metadata
                edges_created += self._create_file_metadata_edges(
                    conn, cursor, relcell_id, file_path, 
                    relative_path, provenance_id
                )
        
        conn.commit()
        conn.close()
        
        print(f"Files ingested: {files_ingested}, Edges created: {edges_created}, Files skipped: {files_skipped}")
        
        return files_ingested, edges_created
    
    def ingest_commit_history(
        self,
        branch: Optional[str] = None,
        max_commits: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Ingest commit history and create commit graph.
        
        Args:
            branch: Branch to extract history from (defaults to current)
            max_commits: Maximum number of commits to process (None = all)
            
        Returns:
            Tuple of (commits_ingested, edges_created)
        """
        if branch is None:
            branch = self.get_current_branch()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        commits_ingested = 0
        edges_created = 0
        
        # Get commits in topological order
        commits = list(self.repo.iter_commits(branch, max_count=max_commits))
        
        for commit in commits:
            # Create virtual cell for commit
            commit_id = f"virtual:commit:{commit.hexsha}"
            relcell_id = get_or_create_virtual_cell(
                conn, cursor, commit_id, "commit"
            )
            
            if relcell_id:
                commits_ingested += 1
                
                # Create provenance for commit edges
                provenance_id = self._create_provenance(
                    conn, branch, commit.hexsha, "commit", 
                    "git_extractor", "1.0"
                )
                
                # Create edges for commit metadata
                edges_created += self._create_commit_edges(
                    conn, cursor, relcell_id, commit, 
                    branch, provenance_id
                )
        
        conn.commit()
        conn.close()
        
        return commits_ingested, edges_created
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches skip pattern."""
        from fnmatch import fnmatch
        return fnmatch(path, pattern) or pattern in path
    
    def _is_ignored(self, path: str) -> bool:
        """
        Check if file is ignored by Git.
        
        Args:
            path: Relative path from repository root
            
        Returns:
            True if file should be ignored, False otherwise
        """
        try:
            # Use git check-ignore to respect .gitignore rules
            # This returns non-empty string if file IS ignored
            result = self.repo.git.check_ignore(path)
            return bool(result)
        except git.exc.GitCommandError:
            # File not ignored (command returns non-zero for non-ignored files)
            return False
        except Exception:
            # If any other error, don't skip the file
            return False
    
    def _get_file_dates_from_git(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get creation and modification dates from Git history.
        
        Args:
            file_path: Relative path from repository root
            
        Returns:
            Tuple of (date_created, date_modified) as ISO strings, or None if not found
        """
        try:
            # Get all commits that touched this file
            commits = list(self.repo.iter_commits(paths=file_path))
            
            if not commits:
                return None, None
            
            # First commit (oldest) = creation date
            date_created = datetime.fromtimestamp(commits[-1].committed_date).isoformat()
            
            # Last commit (newest) = modification date
            date_modified = datetime.fromtimestamp(commits[0].committed_date).isoformat()
            
            return date_created, date_modified
        except Exception:
            # File not in Git history or other error
            return None, None
    
    def _create_provenance(
        self, 
        conn, 
        branch: str, 
        commit_hash: str, 
        source_path: str,
        ingestor: str,
        version: str
    ) -> int:
        """Create provenance record and return ID."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO provenance (
                branch, commit_hash, source_path, ingestor, 
                ingestor_version, extracted_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (branch, commit_hash, source_path, ingestor, 
              version, datetime.now().isoformat()))
        return cursor.lastrowid
    
    def _create_file_relcell(
        self,
        conn,
        cursor,
        branch: str,
        commit_hash: str,
        path: str,
        file_path: Path,
        provenance_id: int
    ) -> Optional[int]:
        """Create RelCell for file."""
        # Check if already exists
        cursor.execute("""
            SELECT id FROM relcells 
            WHERE branch = ? AND commit_hash = ? AND path = ?
        """, (branch, commit_hash, path))
        
        existing = cursor.fetchone()
        if existing:
            return existing[0]
        
        # Get file metadata
        size_bytes = file_path.stat().st_size if file_path.exists() else 0
        checksum = self.compute_file_checksum(file_path)
        mime_type = self.get_mime_type(file_path)
        
        # Determine file type from extension
        suffix = file_path.suffix.lower()
        file_type = suffix[1:] if suffix else "unknown"
        
        # Insert RelCell
        cursor.execute("""
            INSERT INTO relcells (
                branch, commit_hash, path, file_type, mime_type,
                size_bytes, checksum, differentiation_mode, is_virtual, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'git-tree', 0, ?)
        """, (branch, commit_hash, path, file_type, mime_type,
              size_bytes, checksum, datetime.now().isoformat()))
        
        return cursor.lastrowid
    
    def _create_file_metadata_edges(
        self,
        conn,
        cursor,
        relcell_id: int,
        file_path: Path,
        relative_path: Path,
        provenance_id: int
    ) -> int:
        """Create edges for file metadata."""
        edges_created = 0
        
        # File size
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            cursor.execute("""
                INSERT INTO edges (
                    subject_id, predicate, object_literal, provenance_id
                ) VALUES (?, ?, ?, ?)
            """, (relcell_id, "has_size", str(size_bytes), provenance_id))
            edges_created += 1
        
        # MIME type
        mime_type = self.get_mime_type(file_path)
        cursor.execute("""
            INSERT INTO edges (
                subject_id, predicate, object_literal, provenance_id
            ) VALUES (?, ?, ?, ?)
        """, (relcell_id, "has_mime_type", mime_type, provenance_id))
        edges_created += 1
        
        # Checksum
        checksum = self.compute_file_checksum(file_path)
        if checksum:
            cursor.execute("""
                INSERT INTO edges (
                    subject_id, predicate, object_literal, provenance_id
                ) VALUES (?, ?, ?, ?)
            """, (relcell_id, "has_checksum", checksum, provenance_id))
            edges_created += 1
        
        # Directory relationship
        parent_dir = str(relative_path.parent)
        if parent_dir and parent_dir != '.':
            cursor.execute("""
                INSERT INTO edges (
                    subject_id, predicate, object_literal, provenance_id
                ) VALUES (?, ?, ?, ?)
            """, (relcell_id, "file_in_directory", parent_dir, provenance_id))
            edges_created += 1
        
        # Git-sourced date metadata
        date_created, date_modified = self._get_file_dates_from_git(str(relative_path))
        
        if date_created:
            cursor.execute("""
                INSERT INTO edges (
                    subject_id, predicate, object_literal, provenance_id
                ) VALUES (?, ?, ?, ?)
            """, (relcell_id, "date_created", date_created, provenance_id))
            edges_created += 1
        
        if date_modified:
            cursor.execute("""
                INSERT INTO edges (
                    subject_id, predicate, object_literal, provenance_id
                ) VALUES (?, ?, ?, ?)
            """, (relcell_id, "date_modified", date_modified, provenance_id))
            edges_created += 1
        
        return edges_created
    
    def _create_commit_edges(
        self,
        conn,
        cursor,
        commit_relcell_id: int,
        commit: Commit,
        branch: str,
        provenance_id: int
    ) -> int:
        """Create edges for commit metadata."""
        edges_created = 0
        
        # Commit message
        cursor.execute("""
            INSERT INTO edges (
                subject_id, predicate, object_literal, provenance_id
            ) VALUES (?, ?, ?, ?)
        """, (commit_relcell_id, "commit_message", commit.message.strip(), provenance_id))
        edges_created += 1
        
        # Commit timestamp
        commit_time = datetime.fromtimestamp(commit.committed_date).isoformat()
        cursor.execute("""
            INSERT INTO edges (
                subject_id, predicate, object_literal, provenance_id
            ) VALUES (?, ?, ?, ?)
        """, (commit_relcell_id, "committed_at", commit_time, provenance_id))
        edges_created += 1
        
        # Git author (create virtual cell)
        author_email = commit.author.email
        author_id = f"virtual:git-author:{author_email}"
        author_relcell_id = get_or_create_virtual_cell(conn, cursor, author_id, "git-author")
        
        # Create edge: commit -> author
        cursor.execute("""
            INSERT INTO edges (
                subject_id, predicate, object_id, provenance_id
            ) VALUES (?, ?, ?, ?)
        """, (commit_relcell_id, "commit_authored_by", author_relcell_id, provenance_id))
        edges_created += 1
        
        # Author name
        cursor.execute("""
            INSERT OR IGNORE INTO edges (
                subject_id, predicate, object_literal, provenance_id
            ) VALUES (?, ?, ?, ?)
        """, (author_relcell_id, "has_name", commit.author.name, provenance_id))
        edges_created += 1
        
        # Parent commits
        for parent in commit.parents:
            parent_id = f"virtual:commit:{parent.hexsha}"
            parent_relcell_id = get_or_create_virtual_cell(conn, cursor, parent_id, "commit")
            
            cursor.execute("""
                INSERT INTO edges (
                    subject_id, predicate, object_id, provenance_id
                ) VALUES (?, ?, ?, ?)
            """, (parent_relcell_id, "commit_parent_of", commit_relcell_id, provenance_id))
            edges_created += 1
        
        # Branch relationship
        branch_id = f"virtual:branch:{branch}"
        branch_relcell_id = get_or_create_virtual_cell(conn, cursor, branch_id, "branch")
        
        cursor.execute("""
            INSERT INTO edges (
                subject_id, predicate, object_id, provenance_id
            ) VALUES (?, ?, ?, ?)
        """, (commit_relcell_id, "commit_on_branch", branch_relcell_id, provenance_id))
        edges_created += 1
        
        # Branch name
        cursor.execute("""
            INSERT OR IGNORE INTO edges (
                subject_id, predicate, object_literal, provenance_id
            ) VALUES (?, ?, ?, ?)
        """, (branch_relcell_id, "has_name", branch, provenance_id))
        edges_created += 1
        
        return edges_created
