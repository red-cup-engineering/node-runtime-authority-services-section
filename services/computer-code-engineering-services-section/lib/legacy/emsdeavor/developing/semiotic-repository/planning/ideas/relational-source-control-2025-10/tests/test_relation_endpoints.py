"""
Tests for Relation API endpoints.

Verifies that relation endpoints correctly instantiate
Relationing concepts and expose relational structures.
"""

import pytest
from rsc.api.relation import list_citations, get_author_contributions
from rsc.api.relationing_metadata import get_endpoint_metadata


def test_list_citations_metadata():
    """Test that list_citations has correct Relationing metadata."""
    metadata = get_endpoint_metadata(list_citations)
    
    assert metadata is not None
    assert "relation" in metadata.instantiates_terms
    assert "reference" in metadata.instantiates_terms
    assert "cites_internal" in metadata.predicates
    assert "cites_external" in metadata.predicates
    assert "cited_by" in metadata.predicates


def test_get_author_contributions_metadata():
    """Test that get_author_contributions has correct Relationing metadata."""
    metadata = get_endpoint_metadata(get_author_contributions)
    
    assert metadata is not None
    assert "relation" in metadata.instantiates_terms
    assert "authorship" in metadata.instantiates_terms
    assert "agency" in metadata.instantiates_terms
    assert "commit_authored_by" in metadata.predicates
    assert "virtual-synthesis" in metadata.differentiation_modes


def test_list_citations_endpoint(client):
    """Test /api/relation/citations endpoint returns data."""
    response = client.get("/api/relation/citations")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_author_contributions_endpoint(client):
    """Test /api/relation/contributions endpoint returns data."""
    response = client.get("/api/relation/contributions")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
