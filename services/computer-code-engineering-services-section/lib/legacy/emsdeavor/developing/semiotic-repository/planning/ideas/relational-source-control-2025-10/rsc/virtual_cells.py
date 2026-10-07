"""
Virtual cell conventions and utilities.

Virtual cells are RelCells that don't correspond to files but are deterministically
extractable from file content. They enable first-class representation of entities
like terms, authors, and external publications.

All virtual cells must be reproducible: wiping the database and re-ingesting
must recreate identical virtual cells.
"""

from dataclasses import dataclass
from typing import Optional
from .models import RelCell


@dataclass
class VirtualCellConvention:
    """
    Convention for generating virtual cell identifiers.
    
    Virtual cells use a standardized path format for consistency and reconstruction.
    """
    prefix: str
    description: str
    example: str


# Standard virtual cell prefixes
VIRTUAL_CELL_CONVENTIONS = {
    "term": VirtualCellConvention(
        prefix="virtual:term.",
        description="Concept or term defined in documents",
        example="virtual:term.differentiation"
    ),
    "author": VirtualCellConvention(
        prefix="virtual:author.",
        description="Author of documents",
        example="virtual:author.emsenn"
    ),
    "external_publication": VirtualCellConvention(
        prefix="virtual:publication.",
        description="External publication referenced in citations",
        example="virtual:publication.christiano2017"
    ),
    "organization": VirtualCellConvention(
        prefix="virtual:org.",
        description="Organization or institution",
        example="virtual:org.replit"
    )
}


def create_virtual_term_id(term_id: str) -> str:
    """Create a virtual cell ID for a term."""
    return f"virtual:term.{term_id}"


def create_virtual_author_id(author_name: str) -> str:
    """
    Create a virtual cell ID for an author.
    
    Normalizes name by:
    - Converting to lowercase
    - Replacing spaces with hyphens
    - Removing punctuation (periods, commas, apostrophes)
    """
    import re
    normalized_name = author_name.lower()
    normalized_name = re.sub(r'[.,\'"]', '', normalized_name)
    normalized_name = normalized_name.replace(" ", "-")
    return f"virtual:author.{normalized_name}"


def create_virtual_publication_id(citation_key: str) -> str:
    """Create a virtual cell ID for a publication."""
    return f"virtual:publication.{citation_key}"


def create_term_virtual_cell(
    term_id: str,
    branch: str,
    commit: str
) -> RelCell:
    """
    Create a virtual RelCell for a term.
    
    Args:
        term_id: Term identifier (e.g., "term.differentiation")
        branch: Git branch
        commit: Git commit SHA
    
    Returns:
        Virtual RelCell for the term
    """
    # Normalize term_id to ensure consistency
    if not term_id.startswith("term."):
        term_id = f"term.{term_id}"
    
    return RelCell(
        branch=branch,
        commit=commit,
        path=f"virtual:{term_id}",
        is_virtual=True,
        file_type="term"
    )


def create_author_virtual_cell(
    author_name: str,
    branch: str,
    commit: str
) -> RelCell:
    """
    Create a virtual RelCell for an author.
    
    Author IDs are normalized from author names for consistency:
    - Lowercase
    - Replace spaces with hyphens
    - Remove special characters
    
    Args:
        author_name: Author's name (e.g., "emsenn" or "Vine Deloria Jr.")
        branch: Git branch
        commit: Git commit SHA
    
    Returns:
        Virtual RelCell for the author
    """
    # Normalize author name to create consistent ID
    author_id = normalize_author_id(author_name)
    
    return RelCell(
        branch=branch,
        commit=commit,
        path=f"virtual:author.{author_id}",
        is_virtual=True,
        file_type="author"
    )


def create_publication_virtual_cell(
    citation_key: str,
    branch: str,
    commit: str
) -> RelCell:
    """
    Create a virtual RelCell for an external publication.
    
    Args:
        citation_key: Citation key (e.g., "christiano2017")
        branch: Git branch
        commit: Git commit SHA
    
    Returns:
        Virtual RelCell for the publication
    """
    return RelCell(
        branch=branch,
        commit=commit,
        path=f"virtual:publication.{citation_key}",
        is_virtual=True,
        file_type="publication"
    )


def normalize_author_id(author_name: str) -> str:
    """
    Normalize an author name into a consistent identifier.
    
    Rules:
    - Lowercase
    - Replace spaces with hyphens
    - Remove special characters except hyphens
    - Collapse multiple hyphens into one
    
    Examples:
        "emsenn" → "emsenn"
        "Vine Deloria Jr." → "vine-deloria-jr"
        "Paul F. Christiano" → "paul-f-christiano"
    
    Args:
        author_name: Original author name
    
    Returns:
        Normalized author ID
    """
    import re
    
    # Lowercase
    normalized = author_name.lower()
    
    # Replace spaces and dots with hyphens
    normalized = normalized.replace(" ", "-").replace(".", "-")
    
    # Remove all characters except lowercase letters, numbers, and hyphens
    normalized = re.sub(r'[^a-z0-9\-]', '', normalized)
    
    # Collapse multiple hyphens
    normalized = re.sub(r'-+', '-', normalized)
    
    # Remove leading/trailing hyphens
    normalized = normalized.strip('-')
    
    return normalized


def is_virtual_cell(relcell: RelCell) -> bool:
    """Check if a RelCell is virtual."""
    return relcell.is_virtual


def get_virtual_cell_type(relcell: RelCell) -> Optional[str]:
    """
    Get the type of a virtual cell from its path.
    
    Args:
        relcell: RelCell to check
    
    Returns:
        Virtual cell type ("term", "author", "publication", etc.) or None
    """
    if not relcell.is_virtual:
        return None
    
    # Parse virtual:type.id format
    if relcell.path.startswith("virtual:"):
        parts = relcell.path[8:].split(".", 1)
        if parts:
            return parts[0]
    
    return None


def extract_virtual_cell_id(relcell: RelCell) -> Optional[str]:
    """
    Extract the ID portion from a virtual cell path.
    
    Args:
        relcell: Virtual RelCell
    
    Returns:
        ID portion (e.g., "differentiation" from "virtual:term.differentiation")
    """
    if not relcell.is_virtual:
        return None
    
    if relcell.path.startswith("virtual:"):
        parts = relcell.path[8:].split(".", 1)
        if len(parts) == 2:
            return parts[1]
    
    return None
