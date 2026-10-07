from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_dynamics_build realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the lattice.
    flow_map:
        FlowMap carrier whose carrier_id and elements must align with the
        profile lattice.

    Semantics
    ---------
    Realizes ProfileDynamics = (FlowProfile ProfilePhaseSpace) at the carrier
    level by packaging the flow/profile coherence checks into a
    profile_dynamics carrier:

      - profile_topos_id = profile_topos.id
      - flow_map_id = flow_map.id
      - compatibility_checks = {
            "carrier_id_matches": flow_map.carrier_id == profile_topos.id,
            "elements_match": set(flow_map.elements) == set(profile_topos.elements),
        }

    When either check fails, a LawValidationError is raised and no carrier is
    emitted.
    """
    profile_topos = inputs.get("profile_topos")
    flow_map = inputs.get("flow_map")
    if profile_topos is None or flow_map is None:
        raise KeyError("profile_dynamics_build requires 'profile_topos' and 'flow_map' inputs")
    if profile_topos.get("kind") != "profile_topos":
        raise LawValidationError("profile_dynamics_build profile_topos input must have kind 'profile_topos'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("profile_dynamics_build flow_map input must have kind 'flow_map'")

    profile_id = profile_topos["id"]
    carrier_id = flow_map.get("carrier_id")
    if carrier_id != profile_id:
        raise LawValidationError("profile_dynamics_build requires flow_map.carrier_id to equal profile_topos.id")
    profile_elements = set(profile_topos.get("elements", []))
    flow_elements = set(flow_map.get("elements", []))
    if profile_elements != flow_elements:
        raise LawValidationError("profile_dynamics_build requires flow_map.elements to equal profile_topos.elements")

    checks = {
        "carrier_id_matches": True,
        "elements_match": True,
    }
    payload = {
        "kind": "profile_dynamics",
        "profile_topos_id": profile_id,
        "flow_map_id": flow_map["id"],
        "compatibility_checks": checks,
        "act_ref": "ProfileDynamics",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "profile_dynamics_build",
            "src": profile_id,
            "tgt": payload["id"],
        },
        {
            "operator": "profile_dynamics_build",
            "src": flow_map["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"profile_dynamics": payload["id"]},
    )

