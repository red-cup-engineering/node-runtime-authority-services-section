"""
Schema definitions: Enums, constants, and validation rules.

All valid statuses, types, and categories are hardcoded here for validation.
"""

from enum import Enum
from typing import Set


class DocumentStatus(str, Enum):
    """Valid status values for documents."""
    DRAFT = "draft"
    WORKING = "working"
    CANONICAL = "canonical"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class DocumentType(str, Enum):
    """Valid document type classifications."""
    FOUNDATIONAL_TREATISE = "foundational_treatise"
    PAPER = "paper"
    THEOREM = "theorem"
    DEFINITION = "definition"
    PROOF = "proof"
    EXPERIMENT = "experiment"
    NOTE = "note"
    COMMENTARY = "commentary"
    DRAFT = "draft"
    SYNTHESIS = "synthesis"


class SpanType(str, Enum):
    """Types of content spans for provenance."""
    LINE = "line"
    BYTE = "byte"
    AST_PATH = "ast_path"
    FRONTMATTER = "frontmatter"
    ENTIRE_FILE = "entire_file"


class PredicateCategory(str, Enum):
    """Categories for organizing predicates."""
    AUTHORIAL = "authorial"
    TOPICAL = "topical"
    CITATIONAL = "citational"
    RELATIONAL = "relational"
    GIT = "git"
    FILESYSTEM = "filesystem"
    CODE = "code"


class IngestorName:
    """Standard ingestor identifiers."""
    ENDOGENOUS_MARKDOWN_FRONTMATTER = "endogenous.markdown.frontmatter"
    ENDOGENOUS_PYTHON_IMPORTS = "endogenous.python.imports"
    ENDOGENOUS_PYTHON_DECORATORS = "endogenous.python.decorators"
    EXOGENOUS_GIT_AUTHORSHIP = "exogenous.git.authorship"
    EXOGENOUS_GIT_HISTORY = "exogenous.git.history"
    EXOGENOUS_FILESYSTEM_METADATA = "exogenous.filesystem.metadata"


# Valid file extensions for processing
VALID_MARKDOWN_EXTENSIONS: Set[str] = {".md", ".markdown"}
VALID_PYTHON_EXTENSIONS: Set[str] = {".py"}
VALID_EXTENSIONS: Set[str] = VALID_MARKDOWN_EXTENSIONS | VALID_PYTHON_EXTENSIONS


# Citation pattern for inline references
CITATION_PATTERN = r'\[@([a-zA-Z0-9_\-]+)\]'

# ID validation pattern (semantic IDs)
# Allows: lowercase, numbers, hyphens, dots for namespacing
ID_PATTERN = r'^[a-z0-9\-\.]+$'
