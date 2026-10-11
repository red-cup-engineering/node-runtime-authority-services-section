from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    complete_trace realizer.

    Input
    -----
    trace:
        Trace carrier whose elements specify the intended head sequence.

    Semantics
    ---------
    Realizes CompleteTrace by reconstructing a new trace using only the
    StartTrace/AdvanceTrace pattern from relationality.md §3.1: the elements
    list is treated as the finite sequence of heads, and the new trace is
    built by iterated cons from the empty tail.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("complete_trace requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("complete_trace input must have kind 'trace'")

    validate_trace(trace)
    elements: List[str] = list(trace.get("elements", []))
    if not elements:
        raise LawValidationError("complete_trace requires a non-empty trace")

    # Reconstruction: interpret elements as h_0, ..., h_{n-1}. Start from the
    # empty trace and iteratively cons heads, mirroring the abstract
    # construction in §3.1. In the finite case, this yields the same list of
    # elements up to the chosen order; we retain the given sequence.
    new_trace = {
        "kind": "trace",
        "elements": elements,
        "head": elements[0],
        "tail": elements[1:],
    }
    ensure_id_coherence(new_trace)

    steps = [{"index": i, "element": elt} for i, elt in enumerate(elements)]
    evidence = {
        "kind": "complete_trace_evidence",
        "trace_id": new_trace["id"],
        "steps": steps,
        "status": "pass",
        "act_ref": "CompleteTrace",
    }
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "complete_trace",
            "src": trace["id"],
            "tgt": new_trace["id"],
        },
        {
            "operator": "complete_trace",
            "src": new_trace["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[new_trace, evidence],
        edges=edges,
        bindings={"trace": new_trace["id"], "complete_trace_evidence": evidence["id"]},
    )

