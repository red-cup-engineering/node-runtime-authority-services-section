from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_entropy_measure realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the recognition lattice.
    profile_reach:
        ProfileReach carrier describing reachable recognitions.
    entropy_measurement:
        EntropyMeasurement carrier specifying how entropy is measured over a
        given profile.

    Semantics
    ---------
    Acts: ProfileEntropyMeasure = (NucleateProfile ProfileEntropySeed).

    In this code model, we interpret the NucleateProfile collapse as selecting
    a canonical entropy assignment for each profile element consistent with
    the entropy_measurement path and the reachable subset. Concretely:

    - The entropy_measurement.profile_id must equal profile_topos.id.
    - We construct a raw entropy_values mapping by assigning 0.0 to every
      profile element not in profile_reach.reachable_elements and 1.0 to those
      that are reachable; this is a toy but deterministic recognitional
      magnitude compatible with the spec that entropy increases along
      reachable states.

    The resulting profile_entropy carrier is then further propagated along
    traces by ProfileEntropy realizers.
    """
    profile = inputs.get("profile_topos")
    profile_reach = inputs.get("profile_reach")
    entropy_meas = inputs.get("entropy_measurement")
    if profile is None or profile_reach is None or entropy_meas is None:
        raise KeyError(
            "profile_entropy_measure requires 'profile_topos', 'profile_reach', "
            "and 'entropy_measurement' inputs"
        )
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("profile_entropy_measure profile_topos input must have kind 'profile_topos'")
    if profile_reach.get("kind") != "profile_reach":
        raise LawValidationError("profile_entropy_measure profile_reach input must have kind 'profile_reach'")
    if entropy_meas.get("kind") != "entropy_measurement":
        raise LawValidationError("profile_entropy_measure entropy_measurement input must have kind 'entropy_measurement'")

    profile_id = profile["id"]
    if entropy_meas.get("profile_id") != profile_id:
        raise LawValidationError(
            "profile_entropy_measure requires entropy_measurement.profile_id to match profile_topos.id"
        )
    if profile_reach.get("profile_id") != profile_id:
        raise LawValidationError(
            "profile_entropy_measure requires profile_reach.profile_id to match profile_topos.id"
        )

    elements = list(profile.get("elements", []))
    if not elements:
        raise LawValidationError("profile_entropy_measure requires non-empty profile_topos.elements")
    reachable = set(profile_reach.get("reachable_elements") or [])
    element_set = set(elements)
    if not reachable.issubset(element_set):
        raise LawValidationError(
            "profile_entropy_measure requires reachable_elements to be a subset of profile_topos.elements"
        )

    entropy_values = {
        elt: (1.0 if elt in reachable else 0.0)
        for elt in elements
    }

    payload = {
        "kind": "profile_entropy",
        "profile_id": profile_id,
        "entropy_values": entropy_values,
        "act_ref": "ProfileEntropyMeasure",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "profile_entropy_measure",
            "src": profile_id,
            "tgt": payload["id"],
        },
        {
            "operator": "profile_entropy_measure",
            "src": profile_reach["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "profile_entropy_measure",
            "src": entropy_meas["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"profile_entropy": payload["id"]},
    )

