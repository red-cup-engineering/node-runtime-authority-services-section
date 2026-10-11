from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_invariant realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the recognition lattice.
    flow_map:
        FlowMap carrier whose carrier_id must equal profile_topos.id and whose
        elements cover profile_topos.elements.
    nucleus_map:
        NucleusMap carrier on the same lattice; recorded for context but not
        required to fix the invariants themselves (flow-only invariants).
    regime:
        Regime carrier whose id is recorded as regime_ref.

    Semantics
    ---------
    Realizes ProfileInvariant = (StabilizeInvariant ProfileRecognitions) by
    selecting profile recognitions that are fixed points of the profile flow:

        invariant_elements = { x in profile_topos.elements | F(x) = x }.

    The resulting profile_invariant carrier records:
    - the profile it lives over (profile_id),
    - the invariant elements,
    - references to the flow/nucleus/regime carriers used.

    The set of invariants must be non-empty; otherwise a LawValidationError is
    raised.
    """
    profile = inputs.get("profile_topos")
    flow_map = inputs.get("flow_map")
    nucleus_map = inputs.get("nucleus_map")
    regime = inputs.get("regime")
    if profile is None or flow_map is None or nucleus_map is None or regime is None:
        raise KeyError(
            "profile_invariant requires 'profile_topos', 'flow_map', "
            "'nucleus_map', and 'regime' inputs"
        )
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("profile_invariant profile_topos input must have kind 'profile_topos'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("profile_invariant flow_map input must have kind 'flow_map'")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("profile_invariant nucleus_map input must have kind 'nucleus_map'")
    if regime.get("kind") != "regime":
        raise LawValidationError("profile_invariant regime input must have kind 'regime'")

    profile_id = profile["id"]
    profile_elements = list(profile.get("elements", []))
    profile_set = set(profile_elements)

    if flow_map.get("carrier_id") != profile_id:
        raise LawValidationError("profile_invariant requires flow_map.carrier_id == profile_topos.id")
    if nucleus_map.get("carrier_id") != profile_id:
        raise LawValidationError("profile_invariant requires nucleus_map.carrier_id == profile_topos.id")
    flow_elements = set(flow_map.get("elements", []))
    nucleus_elements = set(nucleus_map.get("elements", []))
    if flow_elements != profile_set:
        raise LawValidationError("profile_invariant requires flow_map.elements to equal profile_topos.elements")
    if nucleus_elements != profile_set:
        raise LawValidationError("profile_invariant requires nucleus_map.elements to equal profile_topos.elements")

    flow_table = flow_map.get("flow_table") or {}
    invariant_elements: List[str] = []
    for x in profile_elements:
        image = flow_table.get(x)
        if image is None:
            raise LawValidationError("profile_invariant requires flow_table to be total on profile_topos.elements")
        if image == x:
            invariant_elements.append(x)

    if not invariant_elements:
        raise LawValidationError("profile_invariant found no flow-fixed elements in the profile")

    payload = {
        "kind": "profile_invariant",
        "profile_id": profile_id,
        "invariant_elements": invariant_elements,
        "flow_ref": flow_map["id"],
        "nucleus_ref": nucleus_map["id"],
        "regime_ref": regime["id"],
        "act_ref": "ProfileInvariant",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "profile_invariant",
            "src": profile_id,
            "tgt": payload["id"],
        },
        {
            "operator": "profile_invariant",
            "src": flow_map["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "profile_invariant",
            "src": nucleus_map["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "profile_invariant",
            "src": regime["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"profile_invariant": payload["id"]},
    )

