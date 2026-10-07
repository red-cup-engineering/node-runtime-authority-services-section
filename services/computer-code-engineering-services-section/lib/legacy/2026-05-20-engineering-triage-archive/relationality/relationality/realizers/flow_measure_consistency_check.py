from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    flow_measure_consistency_check realizer.

    Inputs
    ------
    phase_space:
        PhaseSpace carrier (kind ``phase_space``) providing the current state
        and state lattice.
    measurement_frame:
        MeasurementFrame carrier (kind ``measurement_frame``) listing
        admissible observations.
    flow_measure_step:
        Observation carrier (kind ``observation``) produced by FlowMeasureStep.

    Semantics
    ---------
    Witnesses coupling correctness between FlowProfile and MeasurementFrame:

    - flow consistency: flow_measure_step.carrier_id must equal phase_space.id
      and its element must equal phase_space.current_state;
    - measurement consistency: when measurement_frame.admissible_observations
      is non-empty, the observation element must belong to that set.

    Emits flow_measure_consistency_evidence summarizing the check; status is
    'pass' when all conditions hold and 'fail' with a counterexample
    otherwise.
    """
    phase_space = inputs.get("phase_space")
    measurement_frame = inputs.get("measurement_frame")
    obs = inputs.get("flow_measure_step")
    if phase_space is None or measurement_frame is None or obs is None:
        raise KeyError(
            "flow_measure_consistency_check requires 'phase_space', 'measurement_frame', and 'flow_measure_step' inputs"
        )
    if phase_space.get("kind") != "phase_space":
        raise LawValidationError("flow_measure_consistency_check phase_space input must have kind 'phase_space'")
    if measurement_frame.get("kind") != "measurement_frame":
        raise LawValidationError(
            "flow_measure_consistency_check measurement_frame input must have kind 'measurement_frame'"
        )
    if obs.get("kind") != "observation":
        raise LawValidationError(
            "flow_measure_consistency_check flow_measure_step input must have kind 'observation'"
        )

    status = "pass"
    counterexample = None

    # Flow consistency: carrier and element must match the phase space.
    if obs.get("carrier_id") != phase_space["id"]:
        status = "fail"
        counterexample = {
            "reason": "observation.carrier_id does not match phase_space.id",
            "observation_carrier_id": obs.get("carrier_id"),
            "phase_space_id": phase_space["id"],
        }
    else:
        current = phase_space.get("current_state")
        if obs.get("element") != current:
            status = "fail"
            counterexample = {
                "reason": "observation.element does not match phase_space.current_state",
                "observation_element": obs.get("element"),
                "current_state": current,
            }

    # Measurement consistency: admissible_observations, when present, must
    # contain the element.
    if status == "pass":
        admissible = measurement_frame.get("admissible_observations") or []
        element = obs.get("element")
        if admissible and element not in admissible:
            status = "fail"
            counterexample = {
                "reason": "observation.element not in measurement_frame.admissible_observations",
                "element": element,
                "admissible_observations": list(admissible),
            }

    evidence = {
        "kind": "flow_measure_consistency_evidence",
        "phase_space_id": phase_space["id"],
        "measurement_frame_id": measurement_frame["id"],
        "flow_measure_step_id": obs["id"],
        "status": status,
        "act_ref": "FlowMeasureConsistencyCheck",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "flow_measure_consistency_check",
            "src": phase_space["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "flow_measure_consistency_check",
            "src": measurement_frame["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "flow_measure_consistency_check",
            "src": obs["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"flow_measure_consistency_evidence": evidence["id"]},
    )

