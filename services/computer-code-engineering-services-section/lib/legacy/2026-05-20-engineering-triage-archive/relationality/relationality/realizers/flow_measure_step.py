from __future__ import annotations

from typing import Dict

from relationality.realizer_output import RealizerOutput
from relationality.observation_utils import record_observation
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    flow_measure_step realizer.

    Inputs
    ------
    phase_space:
        PhaseSpace carrier whose ``current_state`` is to be measured.
    measurement_frame:
        MeasurementFrame carrier providing admissible observations and kernel
        parameters.

    Semantics
    ---------
    This realizer implements the measurement part of the FlowMeasureStep act
    in the minimal setting where the phase space state is already evolved by
    the flow. It reads the current state of the phase_space and materializes
    a measured Observation whose recognitional element is that state, viewed
    as a recognition in the profile lattice.

    The resulting Observation is required to be admissible with respect to the
    measurement_frame: when ``admissible_observations`` is non-empty, the new
    observation's ID must appear in that set. No heuristic use is made of
    ``kernel_params``; they are part of higher-order analytic acts
    (ObservationKernel) and remain uninterpreted here.
    """
    phase_space = inputs.get("phase_space")
    measurement_frame = inputs.get("measurement_frame")
    if phase_space is None or measurement_frame is None:
        raise KeyError("flow_measure_step requires 'phase_space' and 'measurement_frame' inputs")

    if phase_space.get("kind") != "phase_space":
        raise LawValidationError("flow_measure_step phase_space input must have kind 'phase_space'")
    if measurement_frame.get("kind") != "measurement_frame":
        raise LawValidationError("flow_measure_step measurement_frame input must have kind 'measurement_frame'")

    states = set(phase_space.get("states", []))
    current = phase_space.get("current_state")
    if current not in states:
        raise LawValidationError("flow_measure_step requires phase_space.current_state to be one of the states")

    term_id = None
    judgment_id = None
    constraints = measurement_frame.get("constraints") or {}
    declared_term = constraints.get("term_id")
    if isinstance(declared_term, str):
        term = getattr(graph, "nodes", {}).get(declared_term)
        if term is None or term.get("kind") != "term":
            raise LawValidationError("measurement_frame.constraints.term_id must reference a term in the graph")
        term_id = declared_term
        judgments = [
            n for n in getattr(graph, "nodes", {}).values() if n.get("kind") == "judgment" and n.get("term_id") == term_id
        ]
        if len(judgments) == 1:
            judgment_id = judgments[0]["id"]
    if isinstance(constraints.get("judgment_id"), str):
        judgment_id = constraints["judgment_id"]

    kernel_params = measurement_frame.get("kernel_params") or {}
    # Prefer a measurement_frame-specified element mapping when present.
    carrier_map = kernel_params.get("carrier_to_element") if isinstance(kernel_params, dict) else None
    element = current
    if isinstance(carrier_map, dict):
        mapped = carrier_map.get(phase_space["id"])
        if mapped is not None:
            if not isinstance(mapped, str):
                raise LawValidationError("measurement_frame.kernel_params.carrier_to_element values must be strings")
            element = mapped

    observation = record_observation(
        carrier_id=phase_space["id"],
        measurement_frame_id=measurement_frame["id"],
        element=element,
        act_ref="FlowMeasureStep",
        term_id=term_id,
        judgment_id=judgment_id,
    )

    admissible = measurement_frame.get("admissible_observations", [])
    if admissible:
        if observation["element"] not in admissible:
            raise LawValidationError(
                "flow_measure_step: measured observation element must appear in "
                "measurement_frame.admissible_observations"
            )

    edges = [
        {
            "operator": "flow_measure_step",
            "src": phase_space["id"],
            "tgt": observation["id"],
        },
        {
            "operator": "flow_measure_step",
            "src": measurement_frame["id"],
            "tgt": observation["id"],
        },
    ]

    return RealizerOutput(
        nodes=[observation],
        edges=edges,
        bindings={"observation": observation["id"]},
    )
