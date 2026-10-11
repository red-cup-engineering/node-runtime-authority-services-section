from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    restep_trace realizer.

    Input
    -----
    trace:
        Trace carrier whose renewed head/tail decomposition is to be recorded.

    Semantics
    ---------
    Acts: RestepTrace = (RetailTrace TraceStep).

    In this foundational model, the renewed remainder re-enters the stepping
    act exactly as the current tail. RestepTrace witnesses that the trace
    decomposition into head and tail matches elements = [head] + tail,
    reusing TraceStep laws with a distinct act_ref.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("restep_trace requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("restep_trace input must have kind 'trace'")

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
            "reason": "head/tail do not match elements decomposition",
            "elements": elements,
            "head": head,
            "tail": tail,
        }

    evidence = {
        "kind": "restep_trace_evidence",
        "trace_id": trace["id"],
        "head_element": head,
        "tail_elements": tail,
        "status": status,
        "act_ref": "RestepTrace",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "restep_trace",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"restep_trace_evidence": evidence["id"]},
    )

