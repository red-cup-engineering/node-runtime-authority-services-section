from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    rehead_trace realizer.

    Input
    -----
    trace:
        Trace carrier whose renewed head is to be witnessed.

    Semantics
    ---------
    Acts: ReheadTrace = (RenewTrace HeadTrace).

    In this foundational model, the renewed orientation is represented by the
    existing head of the trace carrier. ReheadTrace therefore witnesses that
    the head element isolates the immediate act of the completed trace,
    reusing the HeadTrace head/tail laws but with a distinct act_ref.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("rehead_trace requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("rehead_trace input must have kind 'trace'")

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
        "kind": "rehead_trace_evidence",
        "trace_id": trace["id"],
        "head_element": head,
        "status": status,
        "act_ref": "ReheadTrace",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "rehead_trace",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"rehead_trace_evidence": evidence["id"]},
    )

