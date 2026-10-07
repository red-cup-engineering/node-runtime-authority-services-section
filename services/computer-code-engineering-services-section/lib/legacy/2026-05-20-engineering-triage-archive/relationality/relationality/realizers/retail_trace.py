from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    retail_trace realizer.

    Input
    -----
    trace:
        Trace carrier whose renewed tail sequence is to be witnessed.

    Semantics
    ---------
    Acts: RetailTrace = (ReheadTrace TailTrace).

    In this foundational model, the renewed tail is represented by the trace
    tail. RetailTrace witnesses that the tail elements are exactly the
    remainder after the renewed head, reusing TailTrace laws with a distinct
    act_ref.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("retail_trace requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("retail_trace input must have kind 'trace'")

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
        "kind": "retail_trace_evidence",
        "trace_id": trace["id"],
        "tail_elements": tail,
        "status": status,
        "act_ref": "RetailTrace",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "retail_trace",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"retail_trace_evidence": evidence["id"]},
    )

