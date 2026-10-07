from __future__ import annotations

import heapq
from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _validate_trace(trace: dict) -> List[str]:
    if trace.get("kind") != "trace":
        raise LawValidationError("shuffle_trace requires input of kind 'trace'")
    elements: List[str] = trace.get("elements", [])
    head = trace.get("head")
    tail = trace.get("tail", [])
    if not isinstance(elements, list) or not elements:
        raise LawValidationError("trace must contain at least one element")
    if elements[0] != head:
        raise LawValidationError("trace violates head = elements[0]")
    if elements[1:] != tail:
        raise LawValidationError("trace violates tail = elements[1:]")
    return elements


def _find_profile_topos(graph, elements: List[str]) -> dict:
    """
    Locate the unique profile_topos carrier whose elements contain all trace
    elements. This realizes the requirement that canonicalization be driven
    by the profile lattice rather than arbitrary lexicographic order.
    """
    candidates: List[dict] = []
    for node in getattr(graph, "nodes", {}).values():
        if node.get("kind") != "profile_topos":
            continue
        carrier_elements = set(node.get("elements", []))
        if all(e in carrier_elements for e in elements):
            candidates.append(node)
    if not candidates:
        raise LawValidationError(
            "shuffle_trace requires a profile_topos whose elements contain all trace elements"
        )
    if len(candidates) > 1:
        raise LawValidationError(
            "shuffle_trace found multiple profile_topos carriers compatible with the trace elements"
        )
    return candidates[0]


def _topos_sort_indices(order: Dict[str, List[str]], elements: List[str]) -> List[int]:
    """
    Compute a total order on trace indices consistent with the profile_topos
    partial order and the original position as a tie-breaker.

    For elements ei, ej:
    - if ei <= ej and not ej <= ei, then ei < ej
    - if incomparable or equal, preserve original order (first occurrence).
    """
    n = len(elements)
    # Build strict order edges between positions based on the lattice order.
    def leq(a: str, b: str) -> bool:
        return b in order.get(a, [])

    successors: Dict[int, List[int]] = {i: [] for i in range(n)}
    indegree: Dict[int, int] = {i: 0 for i in range(n)}
    for i in range(n):
        ai = elements[i]
        for j in range(n):
            if i == j:
                continue
            aj = elements[j]
            if leq(ai, aj) and not leq(aj, ai):
                successors[i].append(j)
                indegree[j] += 1

    # Kahn-style topological sort with original index as tie-breaker.
    heap: List[int] = [i for i in range(n) if indegree[i] == 0]
    heapq.heapify(heap)
    sorted_indices: List[int] = []
    while heap:
        i = heapq.heappop(heap)
        sorted_indices.append(i)
        for j in successors[i]:
            indegree[j] -= 1
            if indegree[j] == 0:
                heapq.heappush(heap, j)

    if len(sorted_indices) != n:
        raise LawValidationError("shuffle_trace order contains a cycle and cannot be topologically sorted")

    return sorted_indices


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    ShuffleTrace realizer.

    Input
    -----
    trace:
        Existing trace carrier.

    Semantics
    ---------
    Apply CollapseShuffle by choosing a canonical representative determined by
    the profile_topos order:

    - Use the profile_topos order to derive a total order on trace elements
      (indices) consistent with the partial order.
    - Break ties (incomparable elements) by first occurrence in the original
      elements list.
    - Set head/tail from this canonical sequence.
    - Record the single permutation that maps original indices to canonical
      indices in shuffle_metadata; canonical_rep is the canonical head.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("shuffle_trace requires `trace` input")
    elements = _validate_trace(trace)

    # Resolve the profile_topos carrier governing the element order.
    profile_topos = _find_profile_topos(graph, elements)
    order_table = profile_topos.get("order", {})

    # Compute canonical index order from the profile_topos.
    sorted_indices = _topos_sort_indices(order_table, elements)
    new_elements = [elements[i] for i in sorted_indices]
    new_head = new_elements[0]
    new_tail = new_elements[1:]

    # Build the single permutation mapping original index -> canonical index.
    index_in_canonical = {old_idx: new_idx for new_idx, old_idx in enumerate(sorted_indices)}
    permutation = [index_in_canonical[i] for i in range(len(elements))]

    new_shuffle: dict = {
        "permutations": [permutation],
        "canonical_rep": new_head,
    }
    new_trace = {
        "kind": "trace",
        "elements": new_elements,
        "head": new_head,
        "tail": new_tail,
        "shuffle_metadata": new_shuffle,
    }
    ensure_id_coherence(new_trace)

    edge = {
        "operator": "shuffle_trace",
        "src": trace["id"],
        "tgt": new_trace["id"],
    }

    return RealizerOutput(
        nodes=[new_trace],
        edges=[edge],
        bindings={"trace": new_trace["id"]},
    )
