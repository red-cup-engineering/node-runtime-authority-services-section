from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .validation import LawValidationError


def find_observation_equivalence(graph, element: str) -> Optional[dict]:
    """
    Locate the unique observation_equivalence carrier whose observation_ids
    contain the given element.

    The search is performed within the current graph instance, so in the
    system_interaction subgraph this is effectively per-System.
    """
    candidates: List[dict] = []
    for node in getattr(graph, "nodes", {}).values():
        if node.get("kind") != "observation_equivalence":
            continue
        ids = node.get("observation_ids", [])
        if element in ids:
            candidates.append(node)
    if not candidates:
        return None
    if len(candidates) > 1:
        raise LawValidationError(
            "multiple observation_equivalence carriers contain the observation element"
        )
    return candidates[0]


def canonicalize_observation_element(eq: dict, element: str) -> Tuple[str, int]:
    """
    Iterate the observation_equivalence.equivalence_table to a fixed point.

    Returns (canonical_element, iteration_count).  Raises LawValidationError
    if the element is not in observation_ids, if the table is missing entries,
    or if normalization does not converge because of a cycle.
    """
    obs_ids = list(eq.get("observation_ids", []))
    obs_set = set(obs_ids)
    if element not in obs_set:
        raise LawValidationError(
            "observation element not present in observation_equivalence.observation_ids"
        )
    table = eq.get("equivalence_table")
    if not isinstance(table, dict):
        raise LawValidationError(
            "observation_equivalence must provide an equivalence_table"
        )
    current = element
    iteration_count = 0
    visited: set[str] = set()
    while True:
        if current in visited:
            raise LawValidationError(
                "observation normalization did not converge: cycle detected in equivalence_table"
            )
        visited.add(current)
        next_element = table.get(current)
        if next_element is None:
            raise LawValidationError(
                "equivalence_table missing entry during observation normalization"
            )
        if next_element == current:
            return current, iteration_count
        iteration_count += 1
        current = next_element


def make_trivial_observation_equivalence(element: str, witness_id: str) -> dict:
    """
    Build a minimal observation_equivalence carrier for a single element.

    This is used when NormalizeObservation encounters an element with no
    existing equivalence carrier in the AOG.  The resulting carrier satisfies
    the full observation_equivalence laws via validation.
    """
    return {
        "kind": "observation_equivalence",
        "observation_ids": [element],
        "equivalence_classes": [[element]],
        "equivalence_table": {element: element},
        "witness_ids": [witness_id],
    }

