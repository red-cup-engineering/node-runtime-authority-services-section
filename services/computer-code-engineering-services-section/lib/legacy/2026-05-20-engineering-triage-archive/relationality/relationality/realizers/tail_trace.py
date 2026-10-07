from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    tail_trace realizer.

    Input
    -----
    trace:
        Trace carrier whose tail sequence is to be witnessed.

    Semantics
    ---------
    Realizes TailTrace by extracting the tail sequence of the supplied trace
    and emitting a tail_trace_evidence carrier:

        tail_elements = trace.tail = trace.elements[1:]

    The evidence records the trace_id, the tail elements, and a pass/fail
    status depending on whether the head/tail invariants hold.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("tail_trace requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("tail_trace input must have kind 'trace'")

    validate_trace(trace)
    elements: List[str] = list(trace.get("elements", []))
    tail = list(trace.get("tail", []))
    tail_matches = bool(elements[1:] == tail)

    status = "pass" if tail_matches else "fail"
    counterexample = None
    if not tail_matches:
        counterexample = {
            "reason": "tail does not match elements[1:]",
            "elements": elements,
            "tail": tail,
        }

    evidence = {
        "kind": "tail_trace_evidence",
        "trace_id": trace["id"],
        "tail_elements": tail,
        "status": status,
        "act_ref": "TailTrace",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "tail_trace",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"tail_trace_evidence": evidence["id"]},
    )

