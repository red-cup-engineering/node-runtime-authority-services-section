from __future__ import annotations

import itertools
from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _validate_trace(trace: dict) -> List[str]:
    if trace.get("kind") != "trace":
        raise LawValidationError("shuffle_equivalence_check requires input of kind 'trace'")
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
    candidates: List[dict] = []
    for node in getattr(graph, "nodes", {}).values():
        if node.get("kind") != "profile_topos":
            continue
        carrier_elements = set(node.get("elements", []))
        if all(e in carrier_elements for e in elements):
            candidates.append(node)
    if not candidates:
        raise LawValidationError(
            "shuffle_equivalence_check requires a profile_topos whose elements contain all trace elements"
        )
    if len(candidates) > 1:
        raise LawValidationError(
            "shuffle_equivalence_check found multiple profile_topos carriers compatible with the trace elements"
        )
    return candidates[0]


def _topos_canonical_elements(order: Dict[str, List[str]], elements: List[str]) -> List[str]:
    """
    Recompute the canonical element ordering for the trace using the same
    profile_topos-based ordering as shuffle_trace.
    """
    n = len(elements)

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
    import heapq

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
        raise LawValidationError(
            "shuffle_equivalence_check: profile_topos order contains a cycle and cannot be topologically sorted"
        )
    return [elements[i] for i in sorted_indices]


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    shuffle_equivalence_check realizer.

    Input
    -----
    trace:
        Existing trace carrier.

    Semantics
    ---------
    Enumerate all admissible shuffles (all permutations of indices) for
    diagnostic purposes, recompute the canonical representative using the
    profile_topos order (the same rule as shuffle_trace), and compare this
    canonical data to the trace's stored head/tail and shuffle_metadata.
    Emit a shuffle_equivalence_evidence node witnessing the result.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("shuffle_equivalence_check requires `trace` input")
    elements = _validate_trace(trace)
    n = len(elements)
    index_universe = list(range(n))
    all_perms: List[List[int]] = [list(p) for p in itertools.permutations(index_universe)]

    # Recompute canonical elements using profile_topos order.
    profile_topos = _find_profile_topos(graph, elements)
    order_table = profile_topos.get("order", {})
    canonical_elements = _topos_canonical_elements(order_table, elements)
    canonical_rep = canonical_elements[0]

    trace_shuffle = trace.get("shuffle_metadata") or {}
    trace_canonical = trace_shuffle.get("canonical_rep")

    counterexample = None
    if trace["elements"] != canonical_elements:
        counterexample = {
            "mode": "elements_mismatch",
            "expected_elements": canonical_elements,
            "given_elements": trace["elements"],
        }
    elif trace_canonical is not None and trace_canonical != canonical_rep:
        counterexample = {
            "mode": "canonical_rep_mismatch",
            "expected": canonical_rep,
            "given": trace_canonical,
        }

    status = "pass" if counterexample is None else "fail"

    evidence = {
        "kind": "shuffle_equivalence_evidence",
        "trace_id": trace["id"],
        "permutations": all_perms,
        "canonical_rep": canonical_rep,
        "status": status,
        "act_ref": "ShuffleTrace/CollapseShuffle",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "shuffle_equivalence_check",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"shuffle_equivalence_evidence": evidence["id"]},
    )
