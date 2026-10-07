"""
Tests for the Relationing metadata layer.

Verifies that decorators correctly attach theory annotations
to endpoints and that the registry system works properly.
"""

import pytest
from rsc.api.relationing_metadata import (
    relationing_cell,
    get_endpoint_metadata,
    get_all_endpoint_metadata,
    instantiates_term,
    queries_mode,
    traverses_predicate,
    RelationingCell
)


def test_relationing_cell_decorator_attaches_metadata():
    """Test that @relationing_cell decorator attaches metadata to functions."""
    
    @relationing_cell(
        instantiates_terms=["recognition", "differentiation"],
        differentiation_modes=["frontmatter"],
        predicates=["has_metadata", "authored_by"],
        closure_type="recognition",
        narrative="Test endpoint for recognition",
        examples=["Example 1", "Example 2"]
    )
    async def test_endpoint():
        return {"test": "data"}
    
    metadata = get_endpoint_metadata(test_endpoint)
    
    assert metadata is not None
    assert isinstance(metadata, RelationingCell)
    assert metadata.instantiates_terms == ["recognition", "differentiation"]
    assert metadata.differentiation_modes == ["frontmatter"]
    assert metadata.predicates == ["has_metadata", "authored_by"]
    assert metadata.closure_type == "recognition"
    assert metadata.narrative == "Test endpoint for recognition"
    assert metadata.examples == ["Example 1", "Example 2"]


def test_relationing_cell_defaults():
    """Test that decorator works with minimal parameters."""
    
    @relationing_cell()
    async def minimal_endpoint():
        return {}
    
    metadata = get_endpoint_metadata(minimal_endpoint)
    
    assert metadata is not None
    assert metadata.instantiates_terms == []
    assert metadata.differentiation_modes == []
    assert metadata.predicates == []
    assert metadata.closure_type is None
    assert metadata.narrative == ""
    assert metadata.examples == []


def test_shorthand_instantiates_term_decorator():
    """Test @instantiates_term shorthand decorator."""
    
    @instantiates_term("recognition")
    async def recognition_endpoint():
        return {}
    
    metadata = get_endpoint_metadata(recognition_endpoint)
    
    assert metadata is not None
    assert metadata.instantiates_terms == ["recognition"]


def test_shorthand_queries_mode_decorator():
    """Test @queries_mode shorthand decorator."""
    
    @queries_mode("frontmatter")
    async def frontmatter_endpoint():
        return {}
    
    metadata = get_endpoint_metadata(frontmatter_endpoint)
    
    assert metadata is not None
    assert metadata.differentiation_modes == ["frontmatter"]


def test_shorthand_traverses_predicate_decorator():
    """Test @traverses_predicate shorthand decorator."""
    
    @traverses_predicate("cites_internal")
    async def citation_endpoint():
        return {}
    
    metadata = get_endpoint_metadata(citation_endpoint)
    
    assert metadata is not None
    assert metadata.predicates == ["cites_internal"]


def test_metadata_persists_through_async_wrapper():
    """Test that metadata is preserved after async wrapper."""
    
    @relationing_cell(
        instantiates_terms=["test"],
        narrative="Test narrative"
    )
    async def wrapped_endpoint():
        return {"result": "success"}
    
    # Metadata should be accessible after wrapping
    metadata = get_endpoint_metadata(wrapped_endpoint)
    assert metadata is not None
    assert metadata.instantiates_terms == ["test"]
    assert metadata.narrative == "Test narrative"


def test_multiple_decorators_on_same_endpoint():
    """Test that multiple decorators compose correctly (outermost/last wins)."""
    
    @relationing_cell(instantiates_terms=["term2"])
    @relationing_cell(instantiates_terms=["term1"])
    async def multi_decorated():
        return {}
    
    metadata = get_endpoint_metadata(multi_decorated)
    
    # Outermost (last applied) decorator wins
    assert metadata is not None
    assert metadata.instantiates_terms == ["term2"]


@pytest.mark.asyncio
async def test_decorated_endpoint_executes_normally():
    """Test that decorated endpoints execute without overhead."""
    
    @relationing_cell(
        instantiates_terms=["recognition"],
        narrative="Test endpoint"
    )
    async def executable_endpoint(value: int):
        return {"doubled": value * 2}
    
    # Should execute normally despite decoration
    result = await executable_endpoint(21)
    assert result == {"doubled": 42}


def test_registry_stores_all_metadata():
    """Test that all decorated endpoints are registered."""
    
    # Get current registry size
    initial_registry = get_all_endpoint_metadata()
    initial_size = len(initial_registry)
    
    # Create new decorated endpoint
    @relationing_cell(instantiates_terms=["new_term"])
    async def new_endpoint():
        return {}
    
    # Registry should have grown
    updated_registry = get_all_endpoint_metadata()
    assert len(updated_registry) > initial_size
    
    # New endpoint should be in registry
    func_key = f"{new_endpoint.__module__}.{new_endpoint.__qualname__}"
    assert func_key in updated_registry
    assert updated_registry[func_key].instantiates_terms == ["new_term"]
