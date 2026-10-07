from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_dynamics_check realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier (kind ``profile_topos``) providing the lattice.
    flow_map:
        FlowMap carrier (kind ``flow_map``) whose carrier_id and elements
        should align with the profile lattice.

    Semantics
    ---------
    ProfileDynamics diagnostic check ensuring:
    - flow_map.carrier_id == profile_topos.id; and
    - set(flow_map.elements) == set(profile_topos.elements).

    Emits profile_dynamics_evidence with status 'pass' when both hold, or
    'fail' with a counterexample otherwise.
    """
    profile_topos = inputs.get("profile_topos")
    flow_map = inputs.get("flow_map")
    if profile_topos is None or flow_map is None:
        raise KeyError("profile_dynamics_check requires 'profile_topos' and 'flow_map' inputs")
    if profile_topos.get("kind") != "profile_topos":
        raise LawValidationError("profile_dynamics_check profile_topos input must have kind 'profile_topos'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("profile_dynamics_check flow_map input must have kind 'flow_map'")

    status = "pass"
    counterexample = None

    profile_id = profile_topos["id"]
    carrier_id = flow_map.get("carrier_id")
    if carrier_id != profile_id:
        status = "fail"
        counterexample = {
            "reason": "flow_map.carrier_id does not match profile_topos.id",
            "flow_carrier_id": carrier_id,
            "profile_topos_id": profile_id,
        }
    else:
        profile_elements = set(profile_topos.get("elements", []))
        flow_elements = set(flow_map.get("elements", []))
        if profile_elements != flow_elements:
            status = "fail"
            counterexample = {
                "reason": "flow_map.elements do not match profile_topos.elements",
                "profile_elements": sorted(profile_elements),
                "flow_elements": sorted(flow_elements),
            }

    evidence = {
        "kind": "profile_dynamics_evidence",
        "profile_topos_id": profile_id,
        "flow_map_id": flow_map["id"],
        "status": status,
        "act_ref": "ProfileDynamicsCheck",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "profile_dynamics_check",
            "src": profile_id,
            "tgt": evidence["id"],
        },
        {
            "operator": "profile_dynamics_check",
            "src": flow_map["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"profile_dynamics_evidence": evidence["id"]},
    )

