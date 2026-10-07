"""
TOML frontmatter parser for Markdown documents.

Extracts and validates the +++...+++ TOML frontmatter block from Markdown files.
"""

import re
import toml
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import asdict
from datetime import datetime

from .models import FrontmatterMetadata, TermDefinition, ExternalCitation
from .schema import DocumentStatus, DocumentType


class FrontmatterParseError(Exception):
    """Raised when frontmatter cannot be parsed."""
    pass


class FrontmatterValidationError(Exception):
    """Raised when frontmatter is invalid."""
    pass


def extract_frontmatter_block(content: str) -> Tuple[Optional[str], str]:
    """
    Extract TOML frontmatter block from Markdown content.
    
    Frontmatter is delimited by +++ ... +++ at the start of the file.
    
    Args:
        content: Full Markdown file content
    
    Returns:
        Tuple of (frontmatter_toml, remaining_content)
        frontmatter_toml is None if no frontmatter found
    
    Example:
        >>> content = "+++\\nid = 'test'\\n+++\\n# Document\\nContent"
        >>> fm, body = extract_frontmatter_block(content)
        >>> fm
        "id = 'test'"
        >>> body
        "# Document\\nContent"
    """
    # Match +++ at start, capture content, match closing +++
    pattern = r'^(?:\s*\n)*\+\+\+\s*\n(.*?)\n\+\+\+\s*\n'
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        return None, content
    
    frontmatter = match.group(1)
    remaining = content[match.end():]
    
    return frontmatter, remaining


def parse_toml_frontmatter(toml_content: str) -> dict:
    """
    Parse TOML frontmatter content.
    
    Args:
        toml_content: TOML string
    
    Returns:
        Parsed dictionary
    
    Raises:
        FrontmatterParseError: If TOML is invalid
    """
    try:
        return toml.loads(toml_content)
    except toml.TomlDecodeError as e:
        raise FrontmatterParseError(f"Invalid TOML: {e}") from e


def validate_document_id(doc_id: str) -> list[str]:
    """
    Validate document ID format.
    
    Rules:
    - Lowercase letters, numbers, hyphens, dots only
    - Must match pattern: ^[a-z0-9\\-\\.]+$
    
    Args:
        doc_id: Document ID to validate
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if not doc_id:
        errors.append("Document ID cannot be empty")
        return errors
    
    pattern = r'^[a-z0-9\-\.]+$'
    if not re.match(pattern, doc_id):
        errors.append(
            f"Document ID '{doc_id}' contains invalid characters. "
            "Must be lowercase letters, numbers, hyphens, and dots only."
        )
    
    return errors


def parse_term_definitions(defines_list: list[dict]) -> list[TermDefinition]:
    """
    Parse [[defines]] blocks into TermDefinition objects.
    
    Args:
        defines_list: List of term definition dictionaries from TOML
    
    Returns:
        List of TermDefinition objects
    
    Raises:
        FrontmatterValidationError: If term definitions are invalid
    """
    terms = []
    
    for idx, term_dict in enumerate(defines_list):
        # STRICT ENFORCEMENT: Reject legacy field names
        if 'term_id' in term_dict:
            raise FrontmatterValidationError(
                f"Term definition {idx} uses deprecated 'term_id' field. "
                "Use 'id' instead. Schema changed: term_id → id, definition → description."
            )
        if 'definition' in term_dict:
            raise FrontmatterValidationError(
                f"Term definition {idx} uses deprecated 'definition' field. "
                "Use 'description' instead. Schema changed: term_id → id, definition → description."
            )
        
        # Validate required fields
        if 'id' not in term_dict:
            raise FrontmatterValidationError(
                f"Term definition {idx} missing required 'id' field"
            )
        if 'label' not in term_dict:
            raise FrontmatterValidationError(
                f"Term definition {idx} missing required 'label' field"
            )
        
        # Validate ID format (no "term." prefix)
        term_id = term_dict['id']
        if term_id.startswith('term.'):
            raise FrontmatterValidationError(
                f"Term ID '{term_id}' should not include 'term.' prefix. "
                "The ingestor will add 'virtual:term.' automatically."
            )
        
        terms.append(TermDefinition(
            id=term_dict['id'],
            label=term_dict['label'],
            description=term_dict.get('description'),
            aliases=term_dict.get('aliases', [])
        ))
    
    return terms


def parse_external_citations(cites_list: list[dict]) -> list[ExternalCitation]:
    """
    Parse [[cites_external]] blocks into ExternalCitation objects.
    
    Args:
        cites_list: List of citation dictionaries from TOML
    
    Returns:
        List of ExternalCitation objects
    
    Raises:
        FrontmatterValidationError: If citations are invalid
    """
    citations = []
    
    for idx, cite_dict in enumerate(cites_list):
        # Validate required fields
        if 'key' not in cite_dict:
            raise FrontmatterValidationError(
                f"External citation {idx} missing required 'key' field"
            )
        if 'title' not in cite_dict:
            raise FrontmatterValidationError(
                f"External citation {idx} missing required 'title' field"
            )
        
        citations.append(ExternalCitation(
            key=cite_dict['key'],
            authors=cite_dict.get('authors', []),
            title=cite_dict['title'],
            year=cite_dict.get('year'),
            venue=cite_dict.get('venue'),
            doi=cite_dict.get('doi'),
            url=cite_dict.get('url'),
            extra=cite_dict.get('extra', {})
        ))
    
    return citations


def validate_frontmatter(data: dict) -> list[str]:
    """
    Validate frontmatter dictionary against schema.
    
    Args:
        data: Parsed TOML frontmatter dictionary
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Required fields
    if 'id' not in data:
        errors.append("Missing required field: 'id'")
    else:
        errors.extend(validate_document_id(data['id']))
    
    if 'title' not in data:
        errors.append("Missing required field: 'title'")
    
    # Validate status if present
    if 'status' in data:
        try:
            DocumentStatus(data['status'])
        except ValueError:
            valid_statuses = [s.value for s in DocumentStatus]
            errors.append(
                f"Invalid status '{data['status']}'. "
                f"Must be one of: {', '.join(valid_statuses)}"
            )
    
    # Validate document_type if present
    if 'document_type' in data:
        try:
            DocumentType(data['document_type'])
        except ValueError:
            valid_types = [t.value for t in DocumentType]
            errors.append(
                f"Invalid document_type '{data['document_type']}'. "
                f"Must be one of: {', '.join(valid_types)}"
            )
    
    # Validate authors is a list
    if 'authors' in data and not isinstance(data['authors'], list):
        errors.append("Field 'authors' must be a list")
    
    # Validate dates format (ISO YYYY-MM-DD)
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    for date_field in ['date_created', 'date_modified']:
        if date_field in data:
            if not isinstance(data[date_field], str):
                errors.append(f"Field '{date_field}' must be a string")
            elif not re.match(date_pattern, data[date_field]):
                errors.append(
                    f"Field '{date_field}' must be ISO format YYYY-MM-DD, "
                    f"got: {data[date_field]}"
                )
    
    return errors


def parse_frontmatter_metadata(data: dict) -> FrontmatterMetadata:
    """
    Convert parsed TOML dictionary to FrontmatterMetadata object.
    
    Args:
        data: Frontmatter dictionary (will be validated)
    
    Returns:
        FrontmatterMetadata object
    
    Raises:
        FrontmatterValidationError: If data is invalid
    """
    # Validate first
    errors = validate_frontmatter(data)
    if errors:
        raise FrontmatterValidationError(
            f"Frontmatter validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )
    
    # Parse nested structures
    defines = []
    if 'defines' in data:
        defines = parse_term_definitions(data['defines'])
    
    cites_external = []
    if 'cites_external' in data:
        cites_external = parse_external_citations(data['cites_external'])
    
    # Extract status and document_type as strings (already validated)
    status = data.get('status', DocumentStatus.DRAFT.value)
    document_type = data.get('document_type')
    
    # Extract all fields, providing defaults
    return FrontmatterMetadata(
        id=data['id'],
        title=data['title'],
        aliases=data.get('aliases', []),
        authors=data.get('authors', []),
        date_created=data.get('date_created'),
        date_modified=data.get('date_modified'),
        status=status,
        document_type=document_type,
        topics=data.get('topics', []),
        disciplines=data.get('disciplines', []),
        cites_internal=data.get('cites_internal', []),
        cited_by_internal=data.get('cited_by_internal', []),
        cites_external=cites_external,
        defines=defines,
        depends_on=data.get('depends_on', []),
        published=data.get('published', False),
        publication_venue=data.get('publication_venue'),
        doi=data.get('doi'),
        license=data.get('license'),
        keywords=data.get('keywords', []),
        git_repo=data.get('git_repo'),
        git_branch=data.get('git_branch'),
        git_commit=data.get('git_commit'),
        extra=data.get('extra', {})
    )


def parse_markdown_file(file_path: Path) -> Tuple[Optional[FrontmatterMetadata], str]:
    """
    Parse a Markdown file with TOML frontmatter.
    
    Args:
        file_path: Path to Markdown file
    
    Returns:
        Tuple of (FrontmatterMetadata, document_body)
        FrontmatterMetadata is None if no frontmatter present
    
    Raises:
        FileNotFoundError: If file doesn't exist
        FrontmatterParseError: If frontmatter TOML is invalid
        FrontmatterValidationError: If frontmatter doesn't match schema
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    content = file_path.read_text(encoding='utf-8')
    
    # Extract frontmatter block
    frontmatter_toml, body = extract_frontmatter_block(content)
    
    if frontmatter_toml is None:
        return None, body
    
    # Parse TOML
    data = parse_toml_frontmatter(frontmatter_toml)
    
    # Convert to FrontmatterMetadata (validation happens inside)
    metadata = parse_frontmatter_metadata(data)
    
    return metadata, body
