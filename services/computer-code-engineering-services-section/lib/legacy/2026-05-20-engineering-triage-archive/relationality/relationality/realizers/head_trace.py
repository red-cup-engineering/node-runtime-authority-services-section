from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    head_trace realizer.

    Input
    -----
    trace:
        Trace carrier whose head element is to be witnessed.

    Semantics
    ---------
    Realizes HeadTrace by extracting the head element of the supplied trace
    and emitting a head_trace_evidence carrier:

        head_element = trace.head = trace.elements[0]

    The evidence records the trace_id, the head element, and a pass/fail
    status depending on whether the head/tail invariants hold.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("head_trace requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("head_trace input must have kind 'trace'")

    validate_trace(trace)
    elements: List[str] = list(trace.get("elements", []))
    head = trace.get("head")
    head_matches = bool(elements and elements[0] == head)

    status = "pass" if head_matches else "fail"
    counterexample = None
    if not head_matches:
        counterexample = {
            "reason": "head does not match elements[0]",
            "elements": elements,
            "head": head,
        }

    evidence = {
        "kind": "head_trace_evidence",
        "trace_id": trace["id"],
        "head_element": head,
        "status": status,
        "act_ref": "HeadTrace",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "head_trace",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"head_trace_evidence": evidence["id"]},
    )

