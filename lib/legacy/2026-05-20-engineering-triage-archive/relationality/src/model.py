from __future__ import annotations

"""
Core datamodel for the semiotic publisher.

Everything in the system is expressed in terms of concepts and atoms.
This module is intentionally free of higher‑level logic so it can be
imported from anywhere without creating cycles.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Feature sets are finite sets of atom ids. Using `frozenset[int]`
# keeps them hashable and emphasises immutability in the semantic core.
FeatureSet = frozenset[int]
AtomId = int


@dataclass
class Atom:
    """Atom a ∈ A representing a primitive feature."""

    id: int
    kind: str
    value: str


@dataclass
class AnnotationTerm:
    """Annotation term mapping vault syntax to definable operators."""

    op: str
    args: List[str]


@dataclass
class Concept:
    """Concept k with fragment and semantic contribution."""

    id: str
    title: str
    path: Path
    body_markdown: str
    metadata: Dict[str, Any]
    annotations: List[AnnotationTerm]
    subjects: Dict[str, str] = field(default_factory=dict)
    facts: List[Tuple[str, str, str]] = field(default_factory=list)
    created: Optional[str] = None
    updated: Optional[str] = None
    folders: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: Optional[str] = None
    type: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    base_features: FeatureSet = field(default_factory=frozenset)
    fragment: FeatureSet = field(default_factory=frozenset)
    semantic: FeatureSet = field(default_factory=frozenset)
    evaluation_score: float = 0.0


@dataclass
class Config:
    """Configurable closure rules and export settings."""

    base_url: str = "http://example.org/"
    site_title: str = "Semiotic Site"
    vault_dir: Optional[str] = None
    output_dir: Optional[str] = None
    mode: str = "site"  # "site" or "doc"
    targets: List[str] = field(default_factory=lambda: ["html", "json", "rdf", "openapi"])
    pandoc_enabled: bool = False
    pandoc_formats: List[str] = field(default_factory=list)
    pandoc_template: Optional[str] = None
    pandoc_filters: List[str] = field(default_factory=list)
    pandoc_output_single: Optional[str] = None
    pandoc_book_title: Optional[str] = None
    ignore: List[str] = field(default_factory=list)
    folder_tag_rules: Dict[str, str] = field(default_factory=dict)
    tag_synonyms: Dict[str, str] = field(default_factory=dict)
    type_tag_rules: Dict[str, str] = field(default_factory=dict)
    status_tag_rules: Dict[str, str] = field(default_factory=dict)
    publish_statuses: List[str] = field(default_factory=list)
    draft_statuses: List[str] = field(default_factory=list)
    lint_strict: bool = False
    # Presentation and project config.
    theme: Optional[str] = None
    projects: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class Universe:
    """Semiotic universe U with atoms, j-relations, and concept registry."""

    atoms: Dict[int, Atom] = field(default_factory=dict)
    atom_index: Dict[Tuple[str, str], int] = field(default_factory=dict)
    next_atom_id: int = 0
    concepts: Dict[str, Concept] = field(default_factory=dict)
    j_relations: Dict[int, Set[int]] = field(default_factory=dict)
    config: Config = field(default_factory=Config)
    indices: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)


__all__ = [
    "Atom",
    "AnnotationTerm",
    "Concept",
    "Config",
    "Universe",
    "FeatureSet",
    "AtomId",
]
