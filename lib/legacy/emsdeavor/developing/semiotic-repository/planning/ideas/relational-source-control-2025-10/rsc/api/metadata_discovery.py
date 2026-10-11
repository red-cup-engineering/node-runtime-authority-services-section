"""
Metadata discovery endpoints.

Exposes the Relationing metadata layer, making the theoretical
foundations of the API queryable and visible in documentation.
"""

from fastapi import APIRouter
from typing import Dict, List, Any

from rsc.api.relationing_metadata import get_all_endpoint_metadata, RelationingCell

router = APIRouter(prefix="/api/metadata", tags=["metadata-discovery"])


@router.get("/relationing")
async def get_relationing_metadata() -> Dict[str, Any]:
    """
    Discover all Relationing metadata annotations.
    
    Returns a complete map of which endpoints instantiate which
    Relationing concepts, making the theoretical foundations of
    the API explicit and queryable.
    
    This endpoint answers questions like:
    - Which endpoints instantiate "recognition"?
    - Which predicates does the API expose?
    - What differentiation modes are queryable?
    - Which operations perform closure?
    """
    metadata_registry = get_all_endpoint_metadata()
    
    # Transform registry into API-friendly structure
    endpoints = {}
    for func_key, metadata in metadata_registry.items():
        # Extract endpoint path from function module/name
        # e.g., "rsc.api.recognition.list_documents" -> "recognition.list_documents"
        parts = func_key.split('.')
        endpoint_name = f"{parts[-2]}.{parts[-1]}" if len(parts) >= 2 else func_key
        
        endpoints[endpoint_name] = {
            "instantiates_terms": metadata.instantiates_terms,
            "differentiation_modes": metadata.differentiation_modes,
            "predicates": metadata.predicates,
            "closure_type": metadata.closure_type,
            "narrative": metadata.narrative,
            "examples": metadata.examples
        }
    
    return {
        "total_annotated_endpoints": len(endpoints),
        "endpoints": endpoints
    }


@router.get("/relationing/terms")
async def get_terms_index() -> Dict[str, List[str]]:
    """
    Index of which endpoints instantiate which Relationing terms.
    
    Returns a reverse index mapping terms to endpoints, useful for
    understanding which API operations embody specific theoretical concepts.
    """
    metadata_registry = get_all_endpoint_metadata()
    
    # Build reverse index: term -> [endpoints]
    term_index: Dict[str, List[str]] = {}
    
    for func_key, metadata in metadata_registry.items():
        parts = func_key.split('.')
        endpoint_name = f"{parts[-2]}.{parts[-1]}" if len(parts) >= 2 else func_key
        
        for term in metadata.instantiates_terms:
            if term not in term_index:
                term_index[term] = []
            term_index[term].append(endpoint_name)
    
    return term_index


@router.get("/relationing/predicates")
async def get_predicates_index() -> Dict[str, List[str]]:
    """
    Index of which endpoints query which predicates.
    
    Returns a reverse index mapping predicates to endpoints,
    showing the relational structure exposed by the API.
    """
    metadata_registry = get_all_endpoint_metadata()
    
    # Build reverse index: predicate -> [endpoints]
    predicate_index: Dict[str, List[str]] = {}
    
    for func_key, metadata in metadata_registry.items():
        parts = func_key.split('.')
        endpoint_name = f"{parts[-2]}.{parts[-1]}" if len(parts) >= 2 else func_key
        
        for predicate in metadata.predicates:
            if predicate not in predicate_index:
                predicate_index[predicate] = []
            predicate_index[predicate].append(endpoint_name)
    
    return predicate_index


@router.get("/relationing/modes")
async def get_modes_index() -> Dict[str, List[str]]:
    """
    Index of which endpoints query which differentiation modes.
    
    Returns a reverse index showing which API operations access
    different types of cells (git-tree, frontmatter, virtual-synthesis).
    """
    metadata_registry = get_all_endpoint_metadata()
    
    # Build reverse index: mode -> [endpoints]
    mode_index: Dict[str, List[str]] = {}
    
    for func_key, metadata in metadata_registry.items():
        parts = func_key.split('.')
        endpoint_name = f"{parts[-2]}.{parts[-1]}" if len(parts) >= 2 else func_key
        
        for mode in metadata.differentiation_modes:
            if mode not in mode_index:
                mode_index[mode] = []
            mode_index[mode].append(endpoint_name)
    
    return mode_index


@router.get("/relationing/summary")
async def get_metadata_summary() -> Dict[str, Any]:
    """
    High-level summary of Relationing metadata coverage.
    
    Shows statistics about how well the API embodies the research theory.
    """
    metadata_registry = get_all_endpoint_metadata()
    
    # Collect unique values
    all_terms = set()
    all_predicates = set()
    all_modes = set()
    closure_types = set()
    
    for metadata in metadata_registry.values():
        all_terms.update(metadata.instantiates_terms)
        all_predicates.update(metadata.predicates)
        all_modes.update(metadata.differentiation_modes)
        if metadata.closure_type:
            closure_types.add(metadata.closure_type)
    
    return {
        "annotated_endpoints": len(metadata_registry),
        "instantiated_terms": sorted(list(all_terms)),
        "exposed_predicates": sorted(list(all_predicates)),
        "queryable_modes": sorted(list(all_modes)),
        "closure_types": sorted(list(closure_types)),
        "coverage": {
            "total_terms": len(all_terms),
            "total_predicates": len(all_predicates),
            "total_modes": len(all_modes)
        }
    }
