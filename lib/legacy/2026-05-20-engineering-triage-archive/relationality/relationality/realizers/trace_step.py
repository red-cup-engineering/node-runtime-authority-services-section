from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    trace_step realizer.

    Input
    -----
    trace:
        Trace carrier whose head/tail decomposition is to be recorded.

    Semantics
    ---------
    Realizes TraceStep = (TailTrace StartTrace) by packaging the head and
    tail of the supplied trace into a trace_step_evidence carrier:

        head_element = trace.head
        tail_elements = trace.tail

    The evidence records the trace_id, head, tail, and a pass/fail status
    depending on whether the decomposition matches elements = [head] + tail.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("trace_step requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("trace_step input must have kind 'trace'")

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
        "kind": "trace_step_evidence",
        "trace_id": trace["id"],
        "head_element": head,
        "tail_elements": tail,
        "status": status,
        "act_ref": "TraceStep",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "trace_step",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"trace_step_evidence": evidence["id"]},
    )

