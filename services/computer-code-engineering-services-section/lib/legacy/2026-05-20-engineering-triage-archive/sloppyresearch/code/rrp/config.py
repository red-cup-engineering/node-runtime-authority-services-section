"""
Configuration management for RRPR.

Handles repository paths, database selection, and system settings.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional


ACTIVE_DB_POINTER = Path(".rrpr-active-db")
DEFAULT_DB_PATH = Path("data/databases/rsc.db")


def _read_active_db_pointer() -> Optional[Path]:
    """Return the currently selected database path recorded on disk (if any)."""
    try:
        text = ACTIVE_DB_POINTER.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not text:
        return None
    return Path(text)


def set_active_db_path(path: Path) -> None:
    """Persist the active database path so subsequent commands use it."""
    ACTIVE_DB_POINTER.write_text(str(path), encoding="utf-8")


@dataclass
class RSCConfig:
    """
    Configuration for the RRPR system.
    
    Attributes:
        repo_root: Root directory of the Git repository to index
        db_path: Path to SQLite database file
        default_branch: Default Git branch to work with
        ingestor_version: Version string for provenance tracking
    """
    repo_root: Path
    db_path: Path
    default_branch: str = "refactor/2025-11"
    ingestor_version: str = "0.1.0"
    
    @classmethod
    def from_env(cls) -> "RSCConfig":
        """
        Create configuration from environment variables or persisted state.
        
        Environment variables:
            RSC_REPO_ROOT: Repository root path (default: current directory)
            RSC_DB_PATH: Database file path (default: pointer or ./data/databases/rsc.db)
            RSC_DEFAULT_BRANCH: Default branch (default: refactor/2025-11)
        """
        repo_root = Path(os.getenv("RSC_REPO_ROOT", "."))

        env_db = os.getenv("RSC_DB_PATH")
        if env_db:
            db_path = Path(env_db)
        else:
            db_path = _read_active_db_pointer() or DEFAULT_DB_PATH

        default_branch = os.getenv("RSC_DEFAULT_BRANCH", "refactor/2025-11")
        
        return cls(
            repo_root=repo_root,
            db_path=db_path,
            default_branch=default_branch
        )
    
    def validate(self) -> list[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.repo_root.exists():
            errors.append(f"Repository root does not exist: {self.repo_root}")
        
        if not self.repo_root.is_dir():
            errors.append(f"Repository root is not a directory: {self.repo_root}")
        
        git_dir = self.repo_root / ".git"
        if not git_dir.exists():
            errors.append(f"Not a Git repository: {self.repo_root}")
        
        db_parent = self.db_path.parent
        if not db_parent.exists():
            errors.append(f"Database parent directory does not exist: {db_parent}")
        
        return errors


def get_default_config() -> RSCConfig:
    """Get default configuration."""
    return RSCConfig.from_env()
