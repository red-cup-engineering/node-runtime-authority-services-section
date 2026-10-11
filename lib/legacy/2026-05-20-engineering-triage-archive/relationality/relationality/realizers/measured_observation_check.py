from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    measured_observation_check realizer.

    Inputs
    ------
    observation:
        Measured Observation carrier (kind ``observation``) produced by
        flow_measure_step.
    measurement_frame:
        MeasurementFrame carrier (kind ``measurement_frame``) against which
        admissibility is checked.

    Semantics
    ---------
    Witnesses FlowMeasureStep correctness by checking that the observation's
    element is admissible for the measurement frame. In the current minimal
    implementation, admissibility is determined solely by membership of
    observation.element in measurement_frame.admissible_observations when
    that set is non-empty.
    """
    observation = inputs.get("observation")
    measurement_frame = inputs.get("measurement_frame")
    if observation is None or measurement_frame is None:
        raise KeyError("measured_observation_check requires 'observation' and 'measurement_frame' inputs")
    if observation.get("kind") != "observation":
        raise LawValidationError("measured_observation_check observation input must have kind 'observation'")
    if measurement_frame.get("kind") != "measurement_frame":
        raise LawValidationError(
            "measured_observation_check measurement_frame input must have kind 'measurement_frame'"
        )

    admissible = measurement_frame.get("admissible_observations", [])
    element = observation.get("element")
    if not isinstance(element, str):
        raise LawValidationError("measured_observation_check requires observation.element to be a string")

    status = "pass"
    counterexample = None
    if admissible and element not in admissible:
        status = "fail"
        counterexample = {
            "reason": "observation.element not in measurement_frame.admissible_observations",
            "element": element,
            "admissible_observations": list(admissible),
        }

    evidence = {
        "kind": "measured_observation_evidence",
        "observation_id": observation["id"],
        "measurement_frame_id": measurement_frame["id"],
        "status": status,
        "act_ref": "MeasuredObservationCheck",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "measured_observation_check",
        "src": observation["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"measured_observation_evidence": evidence["id"]},
    )

