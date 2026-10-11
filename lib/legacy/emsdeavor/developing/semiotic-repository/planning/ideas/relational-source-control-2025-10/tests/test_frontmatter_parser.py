"""
Tests for TOML frontmatter parser.
"""

import pytest
from pathlib import Path
from rsc.frontmatter_parser import (
    extract_frontmatter_block,
    parse_toml_frontmatter,
    validate_document_id,
    parse_frontmatter_metadata,
    parse_markdown_file,
    FrontmatterParseError,
    FrontmatterValidationError
)
from rsc.schema import DocumentStatus, DocumentType


def test_extract_frontmatter_block():
    """Test extracting frontmatter from Markdown content."""
    content = """+++
id = "test-doc"
title = "Test Document"
+++

# Document Content

Here is the body.
"""
    
    fm, body = extract_frontmatter_block(content)
    
    assert fm is not None
    assert 'id = "test-doc"' in fm
    assert 'title = "Test Document"' in fm
    assert body.startswith("# Document Content")


def test_extract_no_frontmatter():
    """Test document without frontmatter."""
    content = "# Document\n\nNo frontmatter here."
    
    fm, body = extract_frontmatter_block(content)
    
    assert fm is None
    assert body == content


def test_parse_toml_frontmatter():
    """Test parsing valid TOML."""
    toml_content = """
id = "test"
title = "Test"
authors = ["alice", "bob"]
"""
    
    data = parse_toml_frontmatter(toml_content)
    
    assert data['id'] == "test"
    assert data['title'] == "Test"
    assert data['authors'] == ["alice", "bob"]


def test_parse_invalid_toml():
    """Test parsing invalid TOML raises error."""
    invalid_toml = """
id = "test"
bad syntax here
"""
    
    with pytest.raises(FrontmatterParseError):
        parse_toml_frontmatter(invalid_toml)


def test_validate_document_id_valid():
    """Test valid document IDs."""
    valid_ids = [
        "simple",
        "with-hyphens",
        "with.dots",
        "mixed-123.test",
        "proposing-relationing"
    ]
    
    for doc_id in valid_ids:
        errors = validate_document_id(doc_id)
        assert len(errors) == 0, f"ID '{doc_id}' should be valid"


def test_validate_document_id_invalid():
    """Test invalid document IDs."""
    invalid_ids = [
        "Has_Uppercase",
        "has spaces",
        "has/slashes",
        "has@symbols",
        ""
    ]
    
    for doc_id in invalid_ids:
        errors = validate_document_id(doc_id)
        assert len(errors) > 0, f"ID '{doc_id}' should be invalid"


def test_parse_proposing_relationing():
    """Test parsing the actual Proposing Relationing document."""
    doc_path = Path("txt/scientific-texts/relations/proposing-relationing.md")
    
    if not doc_path.exists():
        pytest.skip("Proposing Relationing document not found")
    
    metadata, body = parse_markdown_file(doc_path)
    
    assert metadata is not None
    assert metadata.id == "proposing-relationing"
    assert metadata.title == "Proposing Relationing"
    assert "emsenn" in metadata.authors
    assert metadata.status == DocumentStatus.CANONICAL.value
    assert metadata.document_type == DocumentType.FOUNDATIONAL_TREATISE.value
    
    # Check term definitions
    assert len(metadata.defines) > 0
    term_ids = [term.id for term in metadata.defines]
    assert "differentiation" in term_ids
    assert "recognition" in term_ids
    assert "relationing" in term_ids
    
    # Verify no "term." prefix in IDs
    for term in metadata.defines:
        assert not term.id.startswith("term."), \
            f"Term ID should not have 'term.' prefix: {term.id}"
    
    # Check body is present
    assert "Movement I" in body
    assert "Differentiation" in body


def test_term_definition_no_prefix_validation():
    """Test that term IDs with 'term.' prefix are rejected."""
    toml_content = """
id = "test-doc"
title = "Test"

[[defines]]
id = "term.bad-id"
label = "Bad Term"
"""
    
    data = parse_toml_frontmatter(toml_content)
    
    with pytest.raises(FrontmatterValidationError, match="should not include 'term.'"):
        parse_frontmatter_metadata(data)


def test_reject_legacy_term_id_field():
    """Test that legacy 'term_id' field is rejected."""
    toml_content = """
id = "test-doc"
title = "Test"

[[defines]]
term_id = "differentiation"
label = "Differentiation"
description = "Test description"
"""
    
    data = parse_toml_frontmatter(toml_content)
    
    with pytest.raises(FrontmatterValidationError, match="deprecated 'term_id' field"):
        parse_frontmatter_metadata(data)


def test_reject_legacy_definition_field():
    """Test that legacy 'definition' field is rejected."""
    toml_content = """
id = "test-doc"
title = "Test"

[[defines]]
id = "differentiation"
label = "Differentiation"
definition = "Test definition"
"""
    
    data = parse_toml_frontmatter(toml_content)
    
    with pytest.raises(FrontmatterValidationError, match="deprecated 'definition' field"):
        parse_frontmatter_metadata(data)


def test_missing_required_fields():
    """Test validation of missing required fields."""
    # Missing 'id'
    toml_content = """
title = "Test"
"""
    
    data = parse_toml_frontmatter(toml_content)
    
    with pytest.raises(FrontmatterValidationError, match="Missing required field: 'id'"):
        parse_frontmatter_metadata(data)
    
    # Missing 'title'
    toml_content = """
id = "test"
"""
    
    data = parse_toml_frontmatter(toml_content)
    
    with pytest.raises(FrontmatterValidationError, match="Missing required field: 'title'"):
        parse_frontmatter_metadata(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
