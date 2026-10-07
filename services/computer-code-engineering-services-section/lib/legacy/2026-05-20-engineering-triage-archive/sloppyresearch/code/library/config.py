"""
Configuration management for RSC system.

Handles repository paths, database location, and system settings.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class RSCConfig:
    """
    Configuration for the RSC system.
    
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
        Create configuration from environment variables.
        
        Environment variables:
            RSC_REPO_ROOT: Repository root path (default: current directory)
            RSC_DB_PATH: Database file path (default: ./rsc.db)
            RSC_DEFAULT_BRANCH: Default branch (default: refactor/2025-11)
        """
        repo_root = Path(os.getenv("RSC_REPO_ROOT", "."))
        db_path = Path(os.getenv("RSC_DB_PATH", "data/databases/rsc.db"))
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
