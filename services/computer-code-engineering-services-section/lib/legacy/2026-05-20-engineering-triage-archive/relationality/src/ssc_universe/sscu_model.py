from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional, Set, Tuple

from .annterm import AnnTerm, FAIL_BOTTOM, ProvenanceHistory


@dataclasses.dataclass
class Concept:
    const: str
    title: str
    tags: List[str]
    ann: List[AnnTerm]
    body: str
    same_as: List[str]
    publish: bool | List[str] | None = None
    publish_to: List[str] | None = None
    status: str | None = None


@dataclasses.dataclass
class Fragment:
    generators: List[Tuple[object, ProvenanceHistory]]
    elements: Set[object]
    is_failure: bool
    provenance: Dict[object, ProvenanceHistory]


@dataclasses.dataclass
class ClosureTrace:
    steps: List[str]


@dataclasses.dataclass
class SemanticContribution:
    fragment: Fragment
    closure_trace: ClosureTrace


@dataclasses.dataclass
class UniverseInstance:
    concepts: Dict[str, Concept]
    canonical_concepts: Dict[str, Concept]
    equivalence_classes: Dict[str, list[str]]
    groupoid_rep: Dict[str, str]
    fragments: Dict[str, Fragment]
    sem: Dict[str, SemanticContribution]
    failures: Set[object]
    unresolved: List[Tuple[str, str]]  # (source const, target)
    reference_graph: Dict[str, Set[str]]
    config_hash: str
    repo_fingerprint: str
    sanitize_html: bool = True
    html_lang: str = "en"
    source_paths: Dict[str, str] | None = None

    def representative(self, const: str) -> str:
        return self.groupoid_rep.get(const, const)

    def canonical_for(self, const: str) -> Concept:
        rep = self.representative(const)
        return self.canonical_concepts.get(rep, self.concepts[const])

    def sem_fragment(self, const: str) -> Fragment:
        return self.sem[self.representative(const)].fragment


FAIL_ELEMENT = FAIL_BOTTOM
