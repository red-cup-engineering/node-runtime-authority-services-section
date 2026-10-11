"""
Core data models for Relational Source Control.

These models represent the fundamental entities in the RSC system:
- RelCell: A file identified by (branch, commit, path)
- Edge: A relation between RelCells or RelCell and literal
- Provenance: Complete audit trail for edges
- Span: Location within a file
- FrontmatterMetadata: Parsed frontmatter from documents
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import re
from .schema import DocumentStatus, DocumentType, ID_PATTERN


@dataclass(frozen=True)
class Span:
    """
    Location within a file where a claim originates.
    
    Attributes:
        type: Type of span (line, byte, ast_path, frontmatter, entire_file)
        start: Starting position (line number or byte offset)
        end: Ending position (line number or byte offset)
        context: Additional context like "frontmatter.cites_internal[2]"
    """
    type: str
    start: Optional[int] = None
    end: Optional[int] = None
    context: Optional[str] = None
    
    def __str__(self) -> str:
        if self.start is not None and self.end is not None:
            return f"{self.type}:{self.start}-{self.end}"
        elif self.context:
            return f"{self.type}:{self.context}"
        return self.type


@dataclass(frozen=True)
class RelCell:
    """
    A file as identified by (branch, commit_hash, path).
    
    This is the fundamental node type in the RSC graph. Every file in Git
    at a specific commit and branch is a unique RelCell.
    
    Attributes:
        branch: Git branch name
        commit_hash: Git commit SHA
        path: File path relative to repository root
        file_type: File extension (e.g., 'md', 'py')
        mime_type: MIME type of the file
        size_bytes: File size in bytes
        checksum: SHA-256 checksum of content
        is_virtual: Whether this is a virtual cell (not backed by a file)
    """
    branch: str
    commit_hash: str
    path: str
    
    # Optional cached metadata
    file_type: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    is_virtual: bool = False
    
    def __str__(self) -> str:
        if self.is_virtual:
            return f"virtual:{self.path}"
        return f"{self.branch}:{self.commit_hash[:7]}:{self.path}"
    
    def __hash__(self) -> int:
        return hash((self.branch, self.commit_hash, self.path))
    
    @property
    def short_commit(self) -> str:
        """Return first 7 characters of commit SHA."""
        return self.commit_hash[:7] if self.commit_hash else ""


@dataclass(frozen=True)
class Provenance:
    """
    Complete audit trail for an edge.
    
    Every edge must have provenance showing exactly where and how it was extracted.
    
    Attributes:
        branch: Git branch where extraction occurred
        commit_hash: Git commit SHA
        source_path: Path to source file
        span: Location within source file
        ingestor: Name of the ingestor that created this edge
        ingestor_version: Version of the ingestor
        extracted_at: Timestamp of extraction
    """
    branch: str
    commit_hash: str
    source_path: str
    span: Optional[Span]
    ingestor: str
    ingestor_version: str
    extracted_at: datetime
    
    def __str__(self) -> str:
        span_str = f" @{self.span}" if self.span else ""
        return f"{self.source_path}{span_str} via {self.ingestor}"


@dataclass
class Edge:
    """
    A relation between two RelCells (or RelCell and literal).
    
    Represents a triple (subject, predicate, object) with full provenance.
    Object can be either another RelCell or a literal value.
    
    Attributes:
        subject: The RelCell this edge originates from
        predicate: The relationship type
        object_relcell: Target RelCell (if object is a RelCell)
        object_literal: Literal value (if object is a literal)
        provenance: Complete audit trail for this edge
    """
    subject: RelCell
    predicate: str
    object_relcell: Optional[RelCell] = None
    object_literal: Optional[Any] = None
    provenance: Optional[Provenance] = None
    
    def __post_init__(self):
        """Validate that exactly one of object_relcell or object_literal is set."""
        if (self.object_relcell is None) == (self.object_literal is None):
            raise ValueError(
                "Exactly one of object_relcell or object_literal must be provided"
            )
    
    @property
    def object(self) -> Union[RelCell, Any]:
        """Return the object regardless of whether it's a RelCell or literal."""
        return self.object_relcell if self.object_relcell else self.object_literal
    
    @property
    def is_relcell_edge(self) -> bool:
        """True if object is a RelCell, False if literal."""
        return self.object_relcell is not None
    
    def __str__(self) -> str:
        return f"{self.subject} --[{self.predicate}]--> {self.object}"


@dataclass
class ExternalCitation:
    """
    External publication reference with bibliographic information.
    
    Attributes:
        key: Citation key (e.g., 'christiano2017')
        authors: List of author names
        title: Publication title
        year: Publication year
        venue: Journal, conference, or other venue
        doi: Digital Object Identifier
        url: URL to the publication
        extra: Additional fields (volume, pages, etc.)
    """
    key: str
    authors: List[str]
    title: str
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_bibtex_entry(self, entry_type: str = "article") -> str:
        """Generate a BibTeX entry for this citation."""
        lines = [f"@{entry_type}{{{self.key},"]
        
        if self.authors:
            authors_str = " and ".join(self.authors)
            lines.append(f"  author = {{{authors_str}}},")
        
        lines.append(f"  title = {{{self.title}}},")
        
        if self.year:
            lines.append(f"  year = {{{self.year}}},")
        if self.venue:
            lines.append(f"  journal = {{{self.venue}}},")
        if self.doi:
            lines.append(f"  doi = {{{self.doi}}},")
        if self.url:
            lines.append(f"  url = {{{self.url}}},")
        
        for key, value in self.extra.items():
            lines.append(f"  {key} = {{{value}}},")
        
        lines.append("}")
        return "\n".join(lines)


@dataclass
class TermDefinition:
    """
    Definition of a term or concept.
    
    Terms can be extracted from document frontmatter and become virtual cells.
    
    Note: The `id` field should NOT include the "term." prefix - the ingestor
    will add "virtual:term." when creating the virtual RelCell.
    
    Attributes:
        id: Unique identifier for the term (e.g., "differentiation")
        label: Human-readable name (required)
        description: Textual description of the term (optional)
        aliases: Alternative names for the term
    """
    id: str
    label: str
    description: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


@dataclass
class FrontmatterMetadata:
    """
    Parsed frontmatter from Markdown documents.
    
    This represents the TOML frontmatter block that appears at the top
    of Markdown documents. All fields are validated against the schema.
    
    Attributes:
        id: Unique stable identifier (semantic, validated)
        title: Document title
        aliases: Alternative names for the document
        authors: List of author names
        date_created: ISO date string when document was created
        date_modified: ISO date string when last modified
        status: Editorial status (draft, working, canonical, archived)
        document_type: Classification of document type
        topics: Subject areas or topics
        disciplines: Academic disciplines
        cites_internal: List of internal document IDs cited
        cited_by_internal: List of internal documents citing this one
        cites_external: External publication references
        defines: Terms or concepts defined in this document
        depends_on: Concepts this document requires
        published: Whether this is published
        publication_venue: Where it was published
        doi: Digital Object Identifier
        license: License (e.g., 'MIT')
        keywords: Indexing keywords
        git_repo: Git repository URL
        git_branch: Git branch this file is on
        git_commit: Git commit SHA
        extra: Additional custom fields
    """
    # === IDENTITY ===
    id: str
    title: str
    aliases: List[str] = field(default_factory=list)
    
    # === AUTHORIAL ===
    authors: List[str] = field(default_factory=list)
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    status: str = DocumentStatus.DRAFT.value
    
    # === CLASSIFICATION ===
    document_type: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    disciplines: List[str] = field(default_factory=list)
    
    # === CITATIONS ===
    cites_internal: List[str] = field(default_factory=list)
    cited_by_internal: List[str] = field(default_factory=list)
    cites_external: List[ExternalCitation] = field(default_factory=list)
    
    # === RELATIONAL ===
    defines: List[TermDefinition] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    
    # === PUBLICATION ===
    published: bool = False
    publication_venue: Optional[str] = None
    doi: Optional[str] = None
    
    # === ADMINISTRATIVE ===
    license: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    
    # === GIT CONTEXT ===
    git_repo: Optional[str] = None
    git_branch: Optional[str] = None
    git_commit: Optional[str] = None
    
    # === EXTENSIBILITY ===
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def validate_id(self) -> bool:
        """Validate that the ID follows the required pattern."""
        return bool(re.match(ID_PATTERN, self.id))
    
    def validate_status(self) -> bool:
        """Validate that status is a valid DocumentStatus."""
        try:
            DocumentStatus(self.status)
            return True
        except ValueError:
            return False
    
    def validate_document_type(self) -> bool:
        """Validate that document_type is a valid DocumentType if provided."""
        if self.document_type is None:
            return True
        try:
            DocumentType(self.document_type)
            return True
        except ValueError:
            return False
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate all frontmatter fields.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        if not self.validate_id():
            errors.append(f"Invalid ID format: {self.id}. Must match pattern {ID_PATTERN}")
        
        if not self.validate_status():
            valid_statuses = [s.value for s in DocumentStatus]
            errors.append(f"Invalid status: {self.status}. Must be one of {valid_statuses}")
        
        if not self.validate_document_type():
            valid_types = [t.value for t in DocumentType]
            errors.append(f"Invalid document_type: {self.document_type}. Must be one of {valid_types}")
        
        if not self.title:
            errors.append("Title is required")
        
        if not self.authors:
            errors.append("At least one author is required")
        
        return (len(errors) == 0, errors)
