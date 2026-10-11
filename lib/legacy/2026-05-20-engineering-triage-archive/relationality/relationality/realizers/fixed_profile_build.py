from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    fixed_profile_build realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier encoding the judgment lattice.
    flow_map:
        FlowMap carrier encoding F:R→R on the same lattice.
    nucleus_map:
        NucleusMap carrier encoding ν:R→R on the same lattice.

    Semantics
    ---------
    Realizes FixedProfileRecognitions by constructing the set of profile
    recognitions that are fixed points of both flow and nucleus:

        FixedProfileRecognitions = { x | F(x) = x and ν(x) = x }.

    Emits:
    - a fixed_profile carrier listing the fixed recognitions; and
    - fixed_profile_evidence summarizing whether all profile elements are
      fixed or, when not, the first counterexample.
    """
    profile = inputs.get("profile_topos")
    flow_map = inputs.get("flow_map")
    nucleus_map = inputs.get("nucleus_map")
    if profile is None or flow_map is None or nucleus_map is None:
        raise KeyError("fixed_profile_build requires 'profile_topos', 'flow_map', and 'nucleus_map' inputs")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("fixed_profile_build profile_topos input must have kind 'profile_topos'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("fixed_profile_build flow_map input must have kind 'flow_map'")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("fixed_profile_build nucleus_map input must have kind 'nucleus_map'")

    profile_id = profile["id"]
    if flow_map.get("carrier_id") != profile_id or nucleus_map.get("carrier_id") != profile_id:
        raise LawValidationError(
            "fixed_profile_build requires flow_map and nucleus_map to use profile_topos as carrier_id"
        )

    elements: List[str] = list(profile.get("elements", []))
    flow_elements = set(flow_map.get("elements", []))
    nucleus_elements = set(nucleus_map.get("elements", []))
    if set(elements) != flow_elements or set(elements) != nucleus_elements:
        raise LawValidationError(
            "fixed_profile_build requires flow_map.elements and nucleus_map.elements to match profile_topos.elements"
        )

    flow_table = flow_map.get("flow_table") or {}
    nucleus_table = nucleus_map.get("nucleus_table") or {}

    fixed_elements: List[str] = []
    status = "pass"
    counterexample = None
    for x in elements:
        fx = flow_table.get(x)
        nx = nucleus_table.get(x)
        if fx is None or nx is None:
            raise LawValidationError(
                "fixed_profile_build requires total flow and nucleus tables on profile elements"
            )
        if fx == x and nx == x:
            fixed_elements.append(x)
        else:
            status = "fail"
            if counterexample is None:
                counterexample = {
                    "element": x,
                    "flow_image": fx,
                    "nucleus_image": nx,
                }

    if not fixed_elements:
        raise LawValidationError("fixed_profile_build found no elements fixed by both flow and nucleus")

    fixed_profile = {
        "kind": "fixed_profile",
        "profile_topos_id": profile_id,
        "elements": fixed_elements,
        "act_ref": "FixedProfileRecognitions",
    }
    ensure_id_coherence(fixed_profile)

    evidence = {
        "kind": "fixed_profile_evidence",
        "profile_topos_id": profile_id,
        "flow_map_id": flow_map["id"],
        "nucleus_map_id": nucleus_map["id"],
        "status": status,
        "act_ref": "FixedProfileCheck",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "fixed_profile_build",
            "src": profile_id,
            "tgt": fixed_profile["id"],
        },
        {
            "operator": "fixed_profile_build",
            "src": flow_map["id"],
            "tgt": fixed_profile["id"],
        },
        {
            "operator": "fixed_profile_build",
            "src": nucleus_map["id"],
            "tgt": fixed_profile["id"],
        },
        {
            "operator": "fixed_profile_build",
            "src": fixed_profile["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[fixed_profile, evidence],
        edges=edges,
        bindings={
            "fixed_profile": fixed_profile["id"],
            "fixed_profile_evidence": evidence["id"],
        },
    )

