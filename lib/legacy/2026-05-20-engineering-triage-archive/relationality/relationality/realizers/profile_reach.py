from __future__ import annotations

from typing import Dict, List, Set

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _reachable_elements(elements: List[str], flow_table: Dict[str, str]) -> List[str]:
    """
    Compute the forward reachability closure under a total flow_table.

    Starting from every element, follow the flow_table map until cycles, and
    collect all visited states.
    """
    visited: Set[str] = set()
    for start in elements:
        if start in visited:
            continue
        current = start
        while current not in visited:
            visited.add(current)
            current = flow_table[current]
    # Preserve a deterministic ordering using the original element list.
    return [e for e in elements if e in visited]


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_reach realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the recognition lattice.
    flow_map:
        FlowMap carrier restricting the global flow to this profile.

    Semantics
    ---------
    Realizes ProfileReach = (FlowProfile ProfileInvariant) at the carrier
    level by computing the reachability closure of the profile recognitions
    under the profile flow:

        reachable_elements = union of all forward orbits under F.

    The closure is taken starting from every profile element; the result is
    encoded as a subset of profile_topos.elements, with a deterministic order.
    """
    profile = inputs.get("profile_topos")
    flow_map = inputs.get("flow_map")
    if profile is None or flow_map is None:
        raise KeyError("profile_reach requires 'profile_topos' and 'flow_map' inputs")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("profile_reach profile_topos input must have kind 'profile_topos'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("profile_reach flow_map input must have kind 'flow_map'")

    profile_id = profile["id"]
    elements = list(profile.get("elements", []))
    if not elements:
        raise LawValidationError("profile_reach requires profile_topos.elements to be non-empty")
    if flow_map.get("carrier_id") != profile_id:
        raise LawValidationError("profile_reach requires flow_map.carrier_id == profile_topos.id")
    flow_elements = set(flow_map.get("elements", []))
    profile_set = set(elements)
    if flow_elements != profile_set:
        raise LawValidationError("profile_reach requires flow_map.elements to equal profile_topos.elements")

    flow_table = flow_map.get("flow_table") or {}
    if set(flow_table.keys()) != profile_set:
        raise LawValidationError("profile_reach requires flow_table keys to match profile_topos.elements")
    for src, tgt in flow_table.items():
        if tgt not in profile_set:
            raise LawValidationError(
                f"profile_reach flow_table[{src!r}] = {tgt!r} not in profile_topos.elements"
            )

    reachable = _reachable_elements(elements, flow_table)
    if not reachable:
        raise LawValidationError("profile_reach computed an empty reachability set")

    payload = {
        "kind": "profile_reach",
        "profile_id": profile_id,
        "reachable_elements": reachable,
        "flow_ref": flow_map["id"],
        "act_ref": "ProfileReach",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "profile_reach",
            "src": profile_id,
            "tgt": payload["id"],
        },
        {
            "operator": "profile_reach",
            "src": flow_map["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"profile_reach": payload["id"]},
    )

