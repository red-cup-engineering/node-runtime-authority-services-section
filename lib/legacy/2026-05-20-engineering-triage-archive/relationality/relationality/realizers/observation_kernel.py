from __future__ import annotations

from typing import Dict

from relationality.realizer_output import RealizerOutput
from relationality.observation_utils import record_observation
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    observation_kernel realizer.

    Inputs
    ------
    observation:
        Internal Observation node (kind ``observation``).
    measurement_frame:
        MeasurementFrame node (kind ``measurement_frame``) providing admissible
        observations and kernel parameters.

    Semantics
    ---------
    Apply a deterministic observation kernel encoded in
    ``measurement_frame.kernel_params.element_map`` to the observation's
    recognitional element. The admissible set from the measurement frame is
    enforced on both the input and output elements. When no explicit
    element_map is provided, the kernel acts as the identity on elements.

    This realizes the ObservationKernel act in the finite deterministic
    setting where each input element is mapped to exactly one output element.
    """
    observation = inputs.get("observation")
    measurement_frame = inputs.get("measurement_frame")
    if observation is None or measurement_frame is None:
        raise KeyError("observation_kernel requires 'observation' and 'measurement_frame' inputs")

    if observation.get("kind") != "observation":
        raise LawValidationError("observation_kernel observation input must have kind 'observation'")
    if measurement_frame.get("kind") != "measurement_frame":
        raise LawValidationError("observation_kernel measurement_frame input must have kind 'measurement_frame'")

    admissible = set(measurement_frame.get("admissible_observations", []))
    element = observation.get("element")
    if not isinstance(element, str):
        raise LawValidationError("observation_kernel observation.element must be a string")
    if admissible and element not in admissible:
        raise LawValidationError(
            "observation_kernel: input observation.element must be in measurement_frame.admissible_observations"
        )

    params = measurement_frame.get("kernel_params") or {}
    element_map = params.get("element_map")
    if element_map is not None:
        if not isinstance(element_map, dict):
            raise LawValidationError("observation_kernel kernel_params.element_map must be a mapping when present")
        if element not in element_map:
            raise LawValidationError("observation_kernel kernel_params.element_map must provide a mapping for the input element")
        new_element = element_map[element]
        if not isinstance(new_element, str):
            raise LawValidationError("observation_kernel element_map values must be strings")
        if admissible and new_element not in admissible:
            raise LawValidationError(
                "observation_kernel: mapped observation.element must be in measurement_frame.admissible_observations"
            )
    else:
        # Identity kernel in the absence of explicit parameters.
        new_element = element

    new_observation = record_observation(
        carrier_id=observation["carrier_id"],
        measurement_frame_id=measurement_frame["id"],
        element=new_element,
        act_ref="ObservationKernel",
    )

    edges = [
        {
            "operator": "observation_kernel",
            "src": observation["id"],
            "tgt": new_observation["id"],
        },
        {
            "operator": "observation_kernel",
            "src": measurement_frame["id"],
            "tgt": new_observation["id"],
        },
    ]

    return RealizerOutput(
        nodes=[new_observation],
        edges=edges,
        bindings={"observation": new_observation["id"]},
    )
