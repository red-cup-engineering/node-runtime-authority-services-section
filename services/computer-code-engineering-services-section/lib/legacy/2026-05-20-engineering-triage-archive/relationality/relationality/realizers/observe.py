from __future__ import annotations

from typing import Dict

from relationality.realizer_output import RealizerOutput
from relationality.observation_utils import record_observation
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    Observe realizer.

    Inputs
    ------
    observation:
        External ObservationCarrier node (kind ``observation_carrier``).
    measurement_frame:
        MeasurementFrame node (kind ``measurement_frame``) specifying which
        observation carriers are admissible.
    profile_topos:
        ProfileTopos node (kind ``profile_topos``) providing the judgment
        lattice in which the observation is interpreted.

    Semantics
    ---------
    Validate that the supplied ObservationCarrier is admissible for the given
    MeasurementFrame, then materialize an internal Observation node carrying
    references to both carriers. This realizes the Observe act:

        External ObservationCarrier → internal Observation recognition.
    """
    carrier = inputs.get("observation")
    measurement_frame = inputs.get("measurement_frame")
    profile_topos = inputs.get("profile_topos")
    if carrier is None or measurement_frame is None or profile_topos is None:
        raise KeyError("observe requires 'observation', 'measurement_frame', and 'profile_topos' inputs")

    if carrier.get("kind") != "observation_carrier":
        raise LawValidationError("observe input 'observation' must have kind 'observation_carrier'")
    if measurement_frame.get("kind") != "measurement_frame":
        raise LawValidationError("observe input 'measurement_frame' must have kind 'measurement_frame'")
    if profile_topos.get("kind") != "profile_topos":
        raise LawValidationError("observe input 'profile_topos' must have kind 'profile_topos'")

    carrier_id = carrier.get("id")
    if not isinstance(carrier_id, str):
        raise LawValidationError("observation_carrier must provide string 'id'")

    admissible = set(measurement_frame.get("admissible_observations", []))
    # MeasurementFrame expresses admissibility over profile recognitions.
    # kernel_params.carrier_to_element is the explicit act-defined bridge
    # from external carriers to internal recognitions; no heuristic fallback
    # is permitted.
    params = measurement_frame.get("kernel_params") or {}
    carrier_map = params.get("carrier_to_element")
    if not isinstance(carrier_map, dict):
        raise LawValidationError("observe requires measurement_frame.kernel_params.carrier_to_element mapping")
    element = carrier_map.get(carrier_id)
    if element is None:
        raise LawValidationError(
            "observe requires measurement_frame.kernel_params.carrier_to_element "
            "to provide a mapping for the observation_carrier id"
        )
    if not isinstance(element, str):
        raise LawValidationError("carrier_to_element map values must be strings")

    if admissible and element not in admissible:
        raise LawValidationError(
            "observe requires the recognized observation element to appear in "
            "measurement_frame.admissible_observations"
        )
    if element not in set(profile_topos.get("elements", [])):
        raise LawValidationError(
            "observe requires the recognized observation element to be a "
            "profile_topos element"
        )

    constraints = measurement_frame.get("constraints") or {}
    declared_term = constraints.get("term_id")
    term_id = None
    judgment_id = None
    if isinstance(declared_term, str):
        term = getattr(graph, "nodes", {}).get(declared_term)
        if term is None or term.get("kind") != "term":
            raise LawValidationError("measurement_frame.constraints.term_id must reference a term in the graph")
        term_id = declared_term
        # Locate a unique judgment for this term when explicitly declared.
        judgments = [
            n for n in getattr(graph, "nodes", {}).values() if n.get("kind") == "judgment" and n.get("term_id") == term_id
        ]
        if len(judgments) == 1:
            judgment_id = judgments[0]["id"]
        elif len(judgments) > 1:
            raise LawValidationError("measurement_frame.constraints.term_id admits multiple judgments; specify one explicitly")
    if isinstance(constraints.get("judgment_id"), str):
        if judgment_id is not None and judgment_id != constraints["judgment_id"]:
            raise LawValidationError("measurement_frame.constraints.judgment_id conflicts with inferred judgment for term_id")
        judgment_id = constraints["judgment_id"]

    # Materialize the internal Observation recognition via the centralized
    # constructor, which enforces schema shape and canonicalization.
    observation = record_observation(
        carrier_id=carrier_id,
        measurement_frame_id=measurement_frame["id"],
        element=element,
        act_ref="Observe",
        term_id=term_id,
        judgment_id=judgment_id,
    )

    edge = {
        "operator": "observe",
        "src": carrier_id,
        "tgt": observation["id"],
    }

    return RealizerOutput(
        nodes=[observation],
        edges=[edge],
        bindings={"observation": observation["id"]},
    )
