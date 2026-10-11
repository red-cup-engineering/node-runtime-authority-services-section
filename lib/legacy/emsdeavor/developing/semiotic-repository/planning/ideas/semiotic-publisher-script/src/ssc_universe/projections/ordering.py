from __future__ import annotations

from typing import List

from ..sscu_model import UniverseInstance


def canonical_order(instance: UniverseInstance) -> List[dict]:
    """Return canonical concepts ordered deterministically for projections.

    Ordering prefers concept titles (case-insensitive) and then representative
    identifiers. Alias lists are sorted so downstream projections render stable
    provenance and pager sequences.
    """

    ordered = sorted(
        instance.canonical_concepts.items(), key=lambda kv: (kv[1].title.lower(), kv[0])
    )
    return [
        {
            "rep": rep,
            "concept": concept,
            "aliases": [alias for alias in sorted(instance.equivalence_classes.get(rep, [])) if alias != rep],
        }
        for rep, concept in ordered
    ]

