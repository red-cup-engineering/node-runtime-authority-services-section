from __future__ import annotations

"""
Universe operations.

Helpers that work *on* universes regardless of how they were loaded:
- project-based selection (build a smaller project universe from a larger one).
"""

from copy import replace
from typing import Dict, Iterable, Optional

from .markdown_universe import build_indices
from .model import Concept, Universe


def _concept_matches_publish_to(concept: Concept, values: Iterable[str]) -> bool:
    wanted = set(values)
    if not wanted:
        return True
    meta_value = concept.metadata.get("publish_to")
    if isinstance(meta_value, str):
        return meta_value in wanted
    if isinstance(meta_value, (list, tuple)):
        return any(str(v) in wanted for v in meta_value)
    return False


def project_universe(universe: Universe, project_name: str, project_cfg: Dict) -> Universe:
    """
    Build a project-specific universe as a semantic sub-universe of a larger one.

    Currently supports:
    - `publish_to`: frontmatter key listing project names a concept belongs to.
    Other filters can be added later without changing the call sites.
    """
    publish_to_values = project_cfg.get("publish_to", [])

    # Filter concepts by publish_to (if provided).
    selected_concepts: Dict[str, Concept] = {}
    for cid, concept in universe.concepts.items():
        if _concept_matches_publish_to(concept, publish_to_values):
            selected_concepts[cid] = concept

    # Reuse atoms, j-relations, and config; only concepts/indices change.
    project = Universe(
        atoms=universe.atoms,
        atom_index=universe.atom_index,
        next_atom_id=universe.next_atom_id,
        concepts=selected_concepts,
        j_relations=universe.j_relations,
        config=universe.config,
    )
    build_indices(project)
    return project


__all__ = ["project_universe"]

