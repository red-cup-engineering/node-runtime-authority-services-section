"""
Relational Source Control (RSC)

A system for treating Git repositories as queryable relational graphs
where files are nodes (RelCells) and relationships are edges with full provenance.
"""

__version__ = "0.1.0"

from .models import RelCell, Edge, Provenance, Span, FrontmatterMetadata
from .schema import DocumentStatus, DocumentType, SpanType, PredicateCategory
from .virtual_cells import (
    create_term_virtual_cell,
    create_author_virtual_cell,
    create_publication_virtual_cell,
    normalize_author_id
)

__all__ = [
    "RelCell",
    "Edge", 
    "Provenance",
    "Span",
    "FrontmatterMetadata",
    "DocumentStatus",
    "DocumentType",
    "SpanType",
    "PredicateCategory",
    "create_term_virtual_cell",
    "create_author_virtual_cell",
    "create_publication_virtual_cell",
    "normalize_author_id",
]
