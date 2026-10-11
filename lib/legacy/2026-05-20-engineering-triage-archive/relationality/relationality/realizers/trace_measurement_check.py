from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace, validate_object


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    trace_measurement_check realizer.

    Inputs
    ------
    trace:
        Trace carrier providing head/tail decomposition over observation
        recognitions.
    measurement_frame:
        MeasurementFrame carrier listing admissible observations.
    flow_measure_step (optional):
        A FlowMeasureStep output carrier; when provided, its id is recorded
        in the evidence to tie the diagnostic more tightly to a specific
        measurement step.

    Semantics
    ---------
    Realizes the trace-based temporal measurement diagnostic by checking
    that:

    - the trace is a valid temporal carrier (head/tail recursion, non-empty
      elements list when present); and
    - every element recorded in trace.elements is admissible for the given
      measurement_frame (i.e. is listed in
      measurement_frame.admissible_observations).

    On success it emits a trace_measure_evidence node with:
    - trace_id and measurement_frame_id;
    - optional flow_measure_step_id when provided; and
    - status = 'pass'.

    On failure it emits trace_measure_evidence with status = 'fail' and a
    counterexample describing the first offending element (either missing
    from admissible_observations or a structural trace issue) and does not
    raise LawValidationError. Structural mismatches in kinds, however, are
    treated as hard errors.
    """
    trace = inputs.get("trace")
    measurement_frame = inputs.get("measurement_frame")
    flow_measure_step = inputs.get("flow_measure_step")
    if trace is None or measurement_frame is None:
        raise KeyError("trace_measurement_check requires 'trace' and 'measurement_frame' inputs")
    if trace.get("kind") != "trace":
        raise LawValidationError("trace_measurement_check trace input must have kind 'trace'")
    if measurement_frame.get("kind") != "measurement_frame":
        raise LawValidationError("trace_measurement_check measurement_frame input must have kind 'measurement_frame'")
    if flow_measure_step is not None and flow_measure_step.get("kind") != "observation":
        raise LawValidationError(
            "trace_measurement_check flow_measure_step input, when provided, must have kind 'observation'"
        )

    # Structural trace laws first.
    validate_trace(trace)

    elements: List[str] = list(trace.get("elements", []))
    admissible = set(measurement_frame.get("admissible_observations") or [])

    status = "pass"
    counterexample = None

    for idx, elt in enumerate(elements):
        if elt not in admissible:
            status = "fail"
            counterexample = {
                "index": idx,
                "element": elt,
                "reason": "trace element not admissible for measurement_frame",
            }
            break

    evidence: Dict[str, object] = {
        "kind": "trace_measure_evidence",
        "trace_id": trace["id"],
        "measurement_frame_id": measurement_frame["id"],
        "status": status,
        "act_ref": "TraceMeasurementCheck",
    }
    if flow_measure_step is not None:
        evidence["flow_measure_step_id"] = flow_measure_step["id"]
    if counterexample is not None:
        evidence["counterexample"] = counterexample

    ensure_id_coherence(evidence)
    validate_object(evidence)

    edges = [
        {
            "operator": "trace_measurement_check",
            "src": trace["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "trace_measurement_check",
            "src": measurement_frame["id"],
            "tgt": evidence["id"],
        },
    ]
    if flow_measure_step is not None:
        edges.append(
            {
                "operator": "trace_measurement_check",
                "src": flow_measure_step["id"],
                "tgt": evidence["id"],
            }
        )

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"trace_measure_evidence": evidence["id"]},
    )

