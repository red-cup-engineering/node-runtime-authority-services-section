"""
Tests for Recognition API endpoints.

Verifies that recognition endpoints correctly instantiate
Relationing concepts and return expected data.
"""

import pytest
from rsc.api.recognition import list_documents, get_document, list_terms, list_authors
from rsc.api.relationing_metadata import get_endpoint_metadata


def test_list_documents_metadata():
    """Test that list_documents has correct Relationing metadata."""
    metadata = get_endpoint_metadata(list_documents)
    
    assert metadata is not None
    assert "recognition" in metadata.instantiates_terms
    assert "differentiation" in metadata.instantiates_terms
    assert "frontmatter" in metadata.differentiation_modes
    assert "has_metadata" in metadata.predicates
    assert metadata.closure_type == "recognition"
    assert len(metadata.narrative) > 0


def test_get_document_metadata():
    """Test that get_document has correct Relationing metadata."""
    metadata = get_endpoint_metadata(get_document)
    
    assert metadata is not None
    assert "recognition" in metadata.instantiates_terms
    assert "relation" in metadata.instantiates_terms
    assert "frontmatter" in metadata.differentiation_modes
    assert "has_metadata" in metadata.predicates


def test_list_terms_metadata():
    """Test that list_terms has correct Relationing metadata."""
    metadata = get_endpoint_metadata(list_terms)
    
    assert metadata is not None
    assert "recognition" in metadata.instantiates_terms
    assert "reflexive-definition" in metadata.instantiates_terms
    assert "virtual-synthesis" in metadata.differentiation_modes
    assert "defines_term" in metadata.predicates
    assert metadata.closure_type == "recognition"


def test_list_authors_metadata():
    """Test that list_authors has correct Relationing metadata."""
    metadata = get_endpoint_metadata(list_authors)
    
    assert metadata is not None
    assert "recognition" in metadata.instantiates_terms
    assert "authorship" in metadata.instantiates_terms
    assert "frontmatter" in metadata.differentiation_modes
    assert "virtual-synthesis" in metadata.differentiation_modes
    assert metadata.closure_type == "recognition"


def test_list_documents_endpoint(client):
    """Test /api/recognition/documents endpoint returns data."""
    response = client.get("/api/recognition/documents")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_terms_endpoint(client):
    """Test /api/recognition/terms endpoint returns data."""
    response = client.get("/api/recognition/terms")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_authors_endpoint(client):
    """Test /api/recognition/authors endpoint returns data."""
    response = client.get("/api/recognition/authors")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
