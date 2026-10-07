"""
Tests for Metadata Discovery endpoints.

Verifies that metadata discovery endpoints correctly expose
the theoretical foundations of the API.
"""

import pytest


def test_metadata_summary_endpoint(client):
    """Test /api/metadata/relationing/summary endpoint."""
    response = client.get("/api/metadata/relationing/summary")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "annotated_endpoints" in data
    assert "instantiated_terms" in data
    assert "exposed_predicates" in data
    assert "queryable_modes" in data
    assert "coverage" in data
    
    # Should have at least 6 annotated endpoints (from recognition + relation routers)
    assert data["annotated_endpoints"] >= 6
    
    # Should instantiate core Relationing terms
    assert "recognition" in data["instantiated_terms"]
    assert "relation" in data["instantiated_terms"]
    assert "differentiation" in data["instantiated_terms"]


def test_terms_index_endpoint(client):
    """Test /api/metadata/relationing/terms endpoint."""
    response = client.get("/api/metadata/relationing/terms")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should be a dict mapping terms to endpoint lists
    assert isinstance(data, dict)
    
    # Recognition term should map to multiple endpoints
    assert "recognition" in data
    assert isinstance(data["recognition"], list)
    assert len(data["recognition"]) > 0


def test_predicates_index_endpoint(client):
    """Test /api/metadata/relationing/predicates endpoint."""
    response = client.get("/api/metadata/relationing/predicates")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should be a dict mapping predicates to endpoint lists
    assert isinstance(data, dict)
    
    # Core predicates should be present
    assert "has_metadata" in data or "cites_internal" in data


def test_modes_index_endpoint(client):
    """Test /api/metadata/relationing/modes endpoint."""
    response = client.get("/api/metadata/relationing/modes")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should be a dict mapping modes to endpoint lists
    assert isinstance(data, dict)
    
    # Core differentiation modes should be present
    assert "frontmatter" in data or "virtual-synthesis" in data


def test_full_metadata_endpoint(client):
    """Test /api/metadata/relationing endpoint for complete metadata."""
    response = client.get("/api/metadata/relationing")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_annotated_endpoints" in data
    assert "endpoints" in data
    
    # Should have detailed metadata for each endpoint
    assert isinstance(data["endpoints"], dict)
    assert data["total_annotated_endpoints"] > 0
    
    # Pick first endpoint and verify structure
    if data["endpoints"]:
        first_endpoint = list(data["endpoints"].values())[0]
        assert "instantiates_terms" in first_endpoint
        assert "differentiation_modes" in first_endpoint
        assert "predicates" in first_endpoint
        assert "narrative" in first_endpoint


def test_metadata_discovery_makes_api_self_documenting(client):
    """
    Integration test: verify that metadata discovery makes the API
    self-documenting about its theoretical foundations.
    """
    # Get the summary
    summary = client.get("/api/metadata/relationing/summary").json()
    
    # Get terms index
    terms = client.get("/api/metadata/relationing/terms").json()
    
    # Get predicates index
    predicates = client.get("/api/metadata/relationing/predicates").json()
    
    # The API should be able to answer: "Which endpoints instantiate recognition?"
    recognition_endpoints = terms.get("recognition", [])
    assert len(recognition_endpoints) > 0
    
    # The API should be able to answer: "How many predicates does the API expose?"
    predicate_count = summary["coverage"]["total_predicates"]
    assert predicate_count == len(predicates)
    
    # The API should be able to answer: "Which endpoints query citations?"
    citation_predicates = predicates.get("cites_internal", [])
    assert len(citation_predicates) > 0
