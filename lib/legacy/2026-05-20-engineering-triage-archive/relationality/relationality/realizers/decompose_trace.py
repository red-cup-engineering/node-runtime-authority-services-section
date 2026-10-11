from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    decompose_trace realizer.

    Input
    -----
    trace:
        Completed trace carrier.

    Semantics
    ---------
    Realizes DecomposeTrace = (HeadTrace TailTrace) by recording the head and
    tail decomposition of a completed trace:

        head_element = trace.head
        tail_elements = trace.tail

    and checking that these satisfy the recursive shape:

        elements = [head] + tail

    The resulting decompose_trace_evidence carrier witnesses the decomposition
    with a pass/fail status and an optional counterexample when invariants
    are violated.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("decompose_trace requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("decompose_trace input must have kind 'trace'")

    validate_trace(trace)
    elements: List[str] = list(trace.get("elements", []))
    head = trace.get("head")
    tail = list(trace.get("tail", []))

    head_matches = bool(elements and elements[0] == head)
    tail_matches = bool(elements[1:] == tail)

    status = "pass" if (head_matches and tail_matches) else "fail"
    counterexample = None
    if not (head_matches and tail_matches):
        counterexample = {
            "reason": "trace does not decompose as elements = [head] + tail",
            "elements": elements,
            "head": head,
            "tail": tail,
        }

    evidence = {
        "kind": "decompose_trace_evidence",
        "trace_id": trace["id"],
        "head_element": head,
        "tail_elements": tail,
        "status": status,
        "act_ref": "DecomposeTrace",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "decompose_trace",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"decompose_trace_evidence": evidence["id"]},
    )

