from __future__ import annotations

from typing import Dict, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _find_reentry_evidence(nodes: Mapping[str, dict], trace_id: str) -> dict:
    """
    Locate a reentry_trace_evidence node witnessing TraceReentryClosure for
    the given trace_id.
    """
    candidates = [
        node
        for node in nodes.values()
        if node.get("kind") == "reentry_trace_evidence" and node.get("trace_id") == trace_id
    ]
    if not candidates:
        raise LawValidationError(
            "close_judgment_trace requires a reentry_trace_evidence node for the supplied trace"
        )
    # Deterministically select the minimal id.
    return min(candidates, key=lambda n: n["id"])


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    close_judgment_trace realizer.

    Inputs
    ------
    trace:
        Trace carrier already closed under TraceReentryClosure.
    equate_judgment_observation_evidence:
        EquateJudgmentObservationEvidence node witnessing alignment between
        observation and judgment equivalences.

    Semantics
    ---------
    Acts: CloseJudgmentTrace = (TraceReentryClosure EquateJudgmentObservation).

    We realize this by:
    - requiring that the graph contains a reentry_trace_evidence node whose
      trace_id matches the supplied trace and whose status == 'pass';
    - requiring that equate_judgment_observation_evidence.status == 'pass';
    - emitting a close_judgment_trace_evidence carrier recording the trace_id,
      the IDs of both evidences, and overall status == 'pass'.
    """
    trace = inputs.get("trace")
    eq_evidence = inputs.get("equate_judgment_observation_evidence")
    if trace is None or eq_evidence is None:
        raise KeyError(
            "close_judgment_trace requires 'trace' and 'equate_judgment_observation_evidence' inputs"
        )
    if trace.get("kind") != "trace":
        raise LawValidationError("close_judgment_trace trace input must have kind 'trace'")
    if eq_evidence.get("kind") != "equate_judgment_observation_evidence":
        raise LawValidationError(
            "close_judgment_trace equate_judgment_observation_evidence input must have kind "
            "'equate_judgment_observation_evidence'"
        )
    if eq_evidence.get("status") != "pass":
        raise LawValidationError(
            "close_judgment_trace requires equate_judgment_observation_evidence.status == 'pass'"
        )

    nodes = getattr(graph, "nodes", {})
    reentry_evidence = _find_reentry_evidence(nodes, trace["id"])
    if reentry_evidence.get("status") != "pass":
        raise LawValidationError(
            "close_judgment_trace requires reentry_trace_evidence.status == 'pass' for the supplied trace"
        )

    payload = {
        "kind": "close_judgment_trace_evidence",
        "trace_id": trace["id"],
        "equate_judgment_observation_evidence_id": eq_evidence["id"],
        "reentry_trace_evidence_id": reentry_evidence["id"],
        "status": "pass",
        "act_ref": "CloseJudgmentTrace",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "close_judgment_trace",
            "src": trace["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "close_judgment_trace",
            "src": eq_evidence["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "close_judgment_trace",
            "src": reentry_evidence["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"close_judgment_trace_evidence": payload["id"]},
    )

