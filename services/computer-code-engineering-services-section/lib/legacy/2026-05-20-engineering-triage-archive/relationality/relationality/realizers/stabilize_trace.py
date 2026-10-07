from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _validate_trace(trace: dict) -> List[str]:
    if trace.get("kind") != "trace":
        raise LawValidationError("stabilize_trace requires input of kind 'trace'")
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


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    StabilizeTrace realizer.

    Input
    -----
    trace:
        Existing trace carrier.

    Semantics
    ---------
    Apply trace-level closure (TraceObservationEquivalenceClosure composed with
    CompleteTrace) as a canonicalization step. In this foundational
    implementation, stabilization is realized as a fixed-point under the
    current representation: we ensure the trace is already in canonical
    (head, tail, shuffle) form and re-emit it as a stabilized node.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("stabilize_trace requires `trace` input")

    elements = _validate_trace(trace)
    shuffle = trace.get("shuffle_metadata")

    # Enforce that shuffle metadata, if present, is consistent with elements.
    if shuffle is not None:
        perms = shuffle.get("permutations", [])
        for perm in perms:
            if sorted(perm) != list(range(len(elements))):
                raise LawValidationError("stabilize_trace found invalid shuffle permutation")
        canonical_rep = shuffle.get("canonical_rep")
        if canonical_rep is not None and canonical_rep not in elements:
            raise LawValidationError("stabilize_trace canonical_rep must be an element of the trace")

    # Stabilization is idempotent: re-emit the same canonical payload with a
    # recomputed ID to witness closure.
    new_trace = {
        "kind": "trace",
        "elements": list(elements),
        "head": trace["head"],
        "tail": list(trace.get("tail", [])),
    }
    if shuffle is not None:
        new_trace["shuffle_metadata"] = {
            "permutations": [list(p) for p in shuffle.get("permutations", [])],
            "canonical_rep": shuffle.get("canonical_rep"),
        }
    ensure_id_coherence(new_trace)

    edge = {
        "operator": "stabilize_trace",
        "src": trace["id"],
        "tgt": new_trace["id"],
    }

    return RealizerOutput(
        nodes=[new_trace],
        edges=[edge],
        bindings={"trace": new_trace["id"]},
    )

