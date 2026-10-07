from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    continue_trace realizer.

    Input
    -----
    trace:
        Trace carrier whose recursive head/tail structure is to be checked.

    Semantics
    ---------
    Realizes ContinueTrace by witnessing the consistency of the trace
    recursion:

        head_matches_elements: head == elements[0]
        tail_matches_elements: tail == elements[1:]

    The resulting continue_trace_evidence carrier records these booleans and
    a pass/fail status. On well-formed traces produced by StartTrace and
    AdvanceTrace, both checks hold and status == 'pass'.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("continue_trace requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("continue_trace input must have kind 'trace'")

    validate_trace(trace)
    elements: List[str] = list(trace.get("elements", []))
    head = trace.get("head")
    tail = list(trace.get("tail", []))

    head_matches = bool(elements and elements[0] == head)
    tail_matches = bool(elements[1:] == tail)
    checks = {
        "head_matches_elements": head_matches,
        "tail_matches_elements": tail_matches,
    }
    status = "pass" if all(checks.values()) else "fail"
    counterexample = None
    if status == "fail":
        counterexample = {
            "reason": "trace recursion invariants violated",
            "elements": elements,
            "head": head,
            "tail": tail,
        }

    evidence = {
        "kind": "continue_trace_evidence",
        "trace_id": trace["id"],
        "checks": checks,
        "status": status,
        "act_ref": "ContinueTrace",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "continue_trace",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"continue_trace_evidence": evidence["id"]},
    )

