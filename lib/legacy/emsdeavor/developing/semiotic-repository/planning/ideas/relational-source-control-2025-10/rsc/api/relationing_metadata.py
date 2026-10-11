"""
Relationing metadata layer for annotating API endpoints.

This module provides decorators and dataclasses that make explicit
how each API endpoint instantiates Relationing theory concepts.

Core Relationing Concepts:
- Differentiation: The primitive act of being; distinguishing regions
- Recognition: Regions produced by acts of distinction  
- Relation: Edges connecting recognized regions
- Stabilization: Closure operations that produce fixed points
"""

from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any
from functools import wraps


@dataclass
class RelationingCell:
    """
    Metadata describing how an API endpoint embodies a Relationing concept.
    
    This makes explicit which theoretical terms the endpoint instantiates,
    which differentiation mode it queries, and which relational operations
    it performs.
    """
    
    # Core Relationing term(s) this endpoint instantiates
    instantiates_terms: List[str] = field(default_factory=list)
    
    # Differentiation mode(s) queried: "git-tree", "frontmatter", "virtual-synthesis"
    differentiation_modes: List[str] = field(default_factory=list)
    
    # Primary predicate(s) traversed or queried
    predicates: List[str] = field(default_factory=list)
    
    # Type of closure operation: "recognition", "transitive", "reflexive", "symmetric", None
    closure_type: Optional[str] = None
    
    # Narrative description of Relationing semantics
    narrative: str = ""
    
    # Examples from the theory
    examples: List[str] = field(default_factory=list)


# Registry to store metadata for each endpoint
_endpoint_metadata_registry: dict[str, RelationingCell] = {}


def relationing_cell(
    instantiates_terms: List[str] = None,
    differentiation_modes: List[str] = None,
    predicates: List[str] = None,
    closure_type: Optional[str] = None,
    narrative: str = "",
    examples: List[str] = None
) -> Callable:
    """
    Decorator to annotate an API endpoint with Relationing semantics.
    
    This makes the theoretical foundations of each endpoint explicit
    and queryable, demonstrating how the tooling embodies the research.
    
    Usage:
        @router.get("/documents")
        @relationing_cell(
            instantiates_terms=["recognition", "differentiation"],
            differentiation_modes=["frontmatter"],
            predicates=["has_metadata", "authored_by"],
            closure_type="recognition",
            narrative="Enumerates recognized documents as differentiated regions"
        )
        async def list_documents():
            ...
    """
    def decorator(func: Callable) -> Callable:
        metadata = RelationingCell(
            instantiates_terms=instantiates_terms or [],
            differentiation_modes=differentiation_modes or [],
            predicates=predicates or [],
            closure_type=closure_type,
            narrative=narrative,
            examples=examples or []
        )
        
        # Store in registry using function qualified name
        func_key = f"{func.__module__}.{func.__qualname__}"
        _endpoint_metadata_registry[func_key] = metadata
        
        # Attach metadata directly to function for introspection
        func.__relationing_metadata__ = metadata
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # No runtime overhead - just call the original function
            return await func(*args, **kwargs)
        
        # Preserve metadata on wrapper
        wrapper.__relationing_metadata__ = metadata
        
        return wrapper
    
    return decorator


def get_endpoint_metadata(func: Callable) -> Optional[RelationingCell]:
    """Get Relationing metadata for an endpoint function."""
    return getattr(func, '__relationing_metadata__', None)


def get_all_endpoint_metadata() -> dict[str, RelationingCell]:
    """Get all registered endpoint metadata."""
    return _endpoint_metadata_registry.copy()


def instantiates_term(term: str) -> Callable:
    """
    Shorthand decorator to mark that an endpoint instantiates a single term.
    
    Usage:
        @instantiates_term("recognition")
        async def list_documents():
            ...
    """
    return relationing_cell(instantiates_terms=[term])


def queries_mode(mode: str) -> Callable:
    """
    Shorthand decorator to mark which differentiation mode an endpoint queries.
    
    Usage:
        @queries_mode("git-tree")
        async def list_files():
            ...
    """
    return relationing_cell(differentiation_modes=[mode])


def traverses_predicate(predicate: str) -> Callable:
    """
    Shorthand decorator to mark which predicate an endpoint traverses.
    
    Usage:
        @traverses_predicate("cites_internal")
        async def list_citations():
            ...
    """
    return relationing_cell(predicates=[predicate])
