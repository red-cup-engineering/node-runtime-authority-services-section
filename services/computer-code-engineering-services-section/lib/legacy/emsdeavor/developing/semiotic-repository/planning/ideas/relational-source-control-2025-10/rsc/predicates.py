"""
Predicate registry and definitions.

This module defines all core predicates used in the RSC system.
New predicates can be added, but core predicates are versioned and documented here.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
from .schema import PredicateCategory


class Predicate(Enum):
    """Enumeration of core predicate names for easy access."""
    
    AUTHOR = "author"
    HAS_NAME = "has_name"
    CREATED_ON = "created_on"
    MODIFIED_ON = "modified_on"
    HAS_STATUS = "has_status"
    HAS_TITLE = "has_title"
    HAS_ALIAS = "has_alias"
    HAS_TOPIC = "has_topic"
    HAS_DISCIPLINE = "has_discipline"
    HAS_KEYWORD = "has_keyword"
    HAS_DOCUMENT_TYPE = "has_document_type"
    CITES = "cites"
    CITED_BY = "cited_by"
    CITES_EXTERNAL = "cites_external"
    BUILDS_ON = "builds_on"
    DEFINES = "defines"
    HAS_LABEL = "has_label"
    HAS_DESCRIPTION = "has_description"
    DEPENDS_ON = "depends_on"
    
    FILE_AT_COMMIT = "file_at_commit"
    COMMIT_AUTHORED_BY = "commit_authored_by"
    COMMIT_PARENT_OF = "commit_parent_of"
    COMMIT_ON_BRANCH = "commit_on_branch"
    COMMIT_TAGS = "commit_tags"
    FILE_MODIFIED_IN = "file_modified_in"
    FILE_CREATED_IN = "file_created_in"
    FILE_DELETED_IN = "file_deleted_in"
    FILE_RENAMED_TO = "file_renamed_to"
    FILE_IN_DIRECTORY = "file_in_directory"
    COMMIT_MESSAGE = "commit_message"


@dataclass
class PredicateDefinition:
    """
    Definition of a predicate (relationship type).
    
    Attributes:
        name: Predicate identifier (e.g., 'cites', 'author')
        description: Human-readable description
        domain: Expected subject type
        range: Expected object type
        category: Category for organization
        inverse_of: Name of inverse predicate if bidirectional
        is_core: Whether this is a core predicate
    """
    name: str
    description: str
    domain: str
    range: str
    category: PredicateCategory
    inverse_of: Optional[str] = None
    is_core: bool = True


CORE_PREDICATES = {
    # === AUTHORIAL ===
    "author": PredicateDefinition(
        name="author",
        description="Person who authored this document (links to author virtual cell)",
        domain="RelCell",
        range="RelCell[author]",
        category=PredicateCategory.AUTHORIAL,
        is_core=True
    ),
    "has_name": PredicateDefinition(
        name="has_name",
        description="Display name for an entity (author, term, etc.)",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.AUTHORIAL,
        is_core=True
    ),
    "created_on": PredicateDefinition(
        name="created_on",
        description="Date document was created",
        domain="RelCell",
        range="Literal[date]",
        category=PredicateCategory.AUTHORIAL,
        is_core=True
    ),
    "modified_on": PredicateDefinition(
        name="modified_on",
        description="Date document was last modified",
        domain="RelCell",
        range="Literal[date]",
        category=PredicateCategory.AUTHORIAL,
        is_core=True
    ),
    "has_status": PredicateDefinition(
        name="has_status",
        description="Editorial status of document",
        domain="RelCell",
        range="Literal[DocumentStatus]",
        category=PredicateCategory.AUTHORIAL,
        is_core=True
    ),
    "has_title": PredicateDefinition(
        name="has_title",
        description="Title of the document",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.AUTHORIAL,
        is_core=True
    ),
    "has_alias": PredicateDefinition(
        name="has_alias",
        description="Alternative name for the document",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.AUTHORIAL,
        is_core=True
    ),
    
    # === TOPICAL ===
    "has_topic": PredicateDefinition(
        name="has_topic",
        description="Topic or subject area",
        domain="RelCell",
        range="Literal[str] | Term",
        category=PredicateCategory.TOPICAL,
        is_core=True
    ),
    "has_discipline": PredicateDefinition(
        name="has_discipline",
        description="Academic discipline",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.TOPICAL,
        is_core=True
    ),
    "has_keyword": PredicateDefinition(
        name="has_keyword",
        description="Keyword for indexing",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.TOPICAL,
        is_core=True
    ),
    "has_document_type": PredicateDefinition(
        name="has_document_type",
        description="Classification of document type",
        domain="RelCell",
        range="Literal[DocumentType]",
        category=PredicateCategory.TOPICAL,
        is_core=True
    ),
    
    # === CITATIONAL - INTERNAL ===
    "cites": PredicateDefinition(
        name="cites",
        description="References another document in corpus",
        domain="RelCell",
        range="RelCell",
        category=PredicateCategory.CITATIONAL,
        inverse_of="cited_by",
        is_core=True
    ),
    "cited_by": PredicateDefinition(
        name="cited_by",
        description="Is referenced by another document",
        domain="RelCell",
        range="RelCell",
        category=PredicateCategory.CITATIONAL,
        inverse_of="cites",
        is_core=True
    ),
    
    # === CITATIONAL - EXTERNAL ===
    "cites_external": PredicateDefinition(
        name="cites_external",
        description="References external publication",
        domain="RelCell",
        range="Literal[ExternalCitation]",
        category=PredicateCategory.CITATIONAL,
        is_core=True
    ),
    
    # === RELATIONAL/CONCEPTUAL ===
    "defines": PredicateDefinition(
        name="defines",
        description="Introduces or defines a concept/term",
        domain="RelCell",
        range="Term",
        category=PredicateCategory.RELATIONAL,
        is_core=True
    ),
    "depends_on": PredicateDefinition(
        name="depends_on",
        description="Requires understanding of another concept",
        domain="RelCell",
        range="Term | Literal[str]",
        category=PredicateCategory.RELATIONAL,
        is_core=True
    ),
    "builds_on": PredicateDefinition(
        name="builds_on",
        description="Extends or builds upon another document",
        domain="RelCell",
        range="RelCell",
        category=PredicateCategory.RELATIONAL,
        is_core=True
    ),
    
    # === GIT (EXOGENOUS) ===
    "committed_by": PredicateDefinition(
        name="committed_by",
        description="Git commit author",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "committed_at": PredicateDefinition(
        name="committed_at",
        description="Git commit timestamp",
        domain="RelCell",
        range="Literal[datetime]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "git_commit_sha": PredicateDefinition(
        name="git_commit_sha",
        description="Full Git commit SHA",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "git_branch": PredicateDefinition(
        name="git_branch",
        description="Git branch name",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "renamed_from": PredicateDefinition(
        name="renamed_from",
        description="Previous path in Git history",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "file_at_commit": PredicateDefinition(
        name="file_at_commit",
        description="File state at specific commit (links to commit virtual cell)",
        domain="RelCell",
        range="RelCell[commit]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "commit_authored_by": PredicateDefinition(
        name="commit_authored_by",
        description="Commit author (links to git-author virtual cell)",
        domain="RelCell[commit]",
        range="RelCell[git-author]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "commit_parent_of": PredicateDefinition(
        name="commit_parent_of",
        description="Parent commit relationship",
        domain="RelCell[commit]",
        range="RelCell[commit]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "commit_on_branch": PredicateDefinition(
        name="commit_on_branch",
        description="Commit belongs to branch (links to branch virtual cell)",
        domain="RelCell[commit]",
        range="RelCell[branch]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "commit_tags": PredicateDefinition(
        name="commit_tags",
        description="Commit is tagged (links to tag virtual cell)",
        domain="RelCell[commit]",
        range="RelCell[tag]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "file_modified_in": PredicateDefinition(
        name="file_modified_in",
        description="File was modified in commit (links to commit virtual cell)",
        domain="RelCell",
        range="RelCell[commit]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "file_created_in": PredicateDefinition(
        name="file_created_in",
        description="File was created in commit (links to commit virtual cell)",
        domain="RelCell",
        range="RelCell[commit]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "file_deleted_in": PredicateDefinition(
        name="file_deleted_in",
        description="File was deleted in commit (links to commit virtual cell)",
        domain="RelCell",
        range="RelCell[commit]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    "file_renamed_to": PredicateDefinition(
        name="file_renamed_to",
        description="File was renamed to new path",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.GIT,
        inverse_of="renamed_from",
        is_core=True
    ),
    "file_in_directory": PredicateDefinition(
        name="file_in_directory",
        description="File is located in directory",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.FILESYSTEM,
        is_core=True
    ),
    "commit_message": PredicateDefinition(
        name="commit_message",
        description="Git commit message",
        domain="RelCell[commit]",
        range="Literal[str]",
        category=PredicateCategory.GIT,
        is_core=True
    ),
    
    # === FILESYSTEM (EXOGENOUS) ===
    "has_mime_type": PredicateDefinition(
        name="has_mime_type",
        description="MIME type of file",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.FILESYSTEM,
        is_core=True
    ),
    "has_size": PredicateDefinition(
        name="has_size",
        description="File size in bytes",
        domain="RelCell",
        range="Literal[int]",
        category=PredicateCategory.FILESYSTEM,
        is_core=True
    ),
    "has_checksum": PredicateDefinition(
        name="has_checksum",
        description="SHA-256 checksum of file content",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.FILESYSTEM,
        is_core=True
    ),
    
    # === PYTHON CODE (ENDOGENOUS) ===
    "imports": PredicateDefinition(
        name="imports",
        description="Python module imports",
        domain="RelCell",
        range="RelCell | Literal[str]",
        category=PredicateCategory.CODE,
        is_core=True
    ),
    "decorated_with": PredicateDefinition(
        name="decorated_with",
        description="Python decorator applied",
        domain="RelCell",
        range="Literal[str]",
        category=PredicateCategory.CODE,
        is_core=True
    ),
}


def get_predicate(name: str) -> Optional[PredicateDefinition]:
    """Get predicate definition by name."""
    return CORE_PREDICATES.get(name)


def list_predicates_by_category(category: PredicateCategory) -> list[PredicateDefinition]:
    """List all predicates in a given category."""
    return [p for p in CORE_PREDICATES.values() if p.category == category]


def is_valid_predicate(name: str) -> bool:
    """Check if a predicate name is valid (registered)."""
    return name in CORE_PREDICATES
