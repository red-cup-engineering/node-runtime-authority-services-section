from __future__ import annotations

from typing import Dict, List

from relationality.realizer_output import RealizerOutput
from relationality.nucleus_algebra import apply_nucleus
from relationality.observation_utils import record_observation
from relationality.validation import LawValidationError


def _load_profile_topos(graph, nucleus_map: dict) -> dict:
    """
    Resolve and sanity-check the profile_topos carrier for a nucleus_map.
    """
    carrier_id = nucleus_map.get("carrier_id")
    if not isinstance(carrier_id, str):
        raise LawValidationError("nucleus_map must declare a string carrier_id")
    carrier = graph.nodes.get(carrier_id)
    if carrier is None:
        raise KeyError(f"carrier {carrier_id} referenced by nucleus_map not found in graph")
    if carrier.get("kind") != "profile_topos":
        raise LawValidationError("nucleus_map carrier must be a profile_topos")
    elements: List[str] = list(carrier.get("elements", []))
    nucleus_elements = set(nucleus_map.get("elements", []))
    if set(elements) != nucleus_elements:
        raise LawValidationError("nucleus_map elements must match profile_topos elements exactly")
    return carrier


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    nucleate_profile realizer.

    Inputs
    ------
    observation:
        Internal Observation node (kind ``observation``) whose recognitional
        element is to be closed.
    nucleus_map:
        NucleusMap node (kind ``nucleus_map``) whose carrier is the
        profile_topos providing the profile nucleus ν.

    Semantics
    ---------
    Apply the profile nucleus ν to the observation's recognitional element,
    yielding a new Observation whose element lies in the nucleus-closed
    profile. This realizes NucleateProfile = (Nucleate ProfileRecognitions)
    at the carrier level.
    """
    observation = inputs.get("observation")
    nucleus_map = inputs.get("nucleus_map")
    if observation is None or nucleus_map is None:
        raise KeyError("nucleate_profile requires 'observation' and 'nucleus_map' inputs")

    if observation.get("kind") != "observation":
        raise LawValidationError("nucleate_profile observation input must have kind 'observation'")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("nucleate_profile nucleus_map input must have kind 'nucleus_map'")

    carrier = _load_profile_topos(graph, nucleus_map)
    element = observation.get("element")
    if not isinstance(element, str):
        raise LawValidationError("observation must provide string 'element'")

    closed_element = apply_nucleus(nucleus_map, element)
    if closed_element not in carrier["elements"]:
        raise LawValidationError("closed element not in profile_topos elements")

    new_observation = record_observation(
        carrier_id=observation["carrier_id"],
        measurement_frame_id=observation["measurement_frame_id"],
        element=closed_element,
        act_ref="NucleateProfile",
    )

    edges = [
        {
            "operator": "nucleate_profile",
            "src": observation["id"],
            "tgt": new_observation["id"],
        },
        {
            "operator": "nucleate_profile",
            "src": nucleus_map["id"],
            "tgt": new_observation["id"],
        },
    ]

    return RealizerOutput(
        nodes=[new_observation],
        edges=edges,
        bindings={"observation": new_observation["id"]},
    )
