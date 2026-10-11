from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    geometry_profile realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos lattice on which the profile geometry is defined.
    flow_map:
        FlowMap encoding F_profile on the profile lattice.
    nucleus_map:
        NucleusMap encoding ν_profile on the same lattice.
    flow_laws_evidence:
        Evidence that the flow_map satisfies the flow laws on the carrier.
    nucleus_laws_evidence:
        Evidence that the nucleus_map satisfies the nucleus laws on the carrier.
    commutation_evidence:
        Evidence that F_profile and ν_profile commute pointwise on the carrier.

    Semantics
    ---------
    GeometryProfile = (FlowProfile NucleateProfile) packages the pair
    (F_profile, ν_profile) as a geometry on the profile: a commuting flow/nucleus
    pair satisfying the structural laws on the profile lattice.

    This realizer therefore:
    - checks that flow_map and nucleus_map share the profile_topos as carrier and
      have the same element set as the profile lattice;
    - requires flow_laws_evidence, nucleus_laws_evidence, and commutation_evidence
      to certify the corresponding laws on that lattice; and
    - emits a geometry_profile carrier that references the profile, maps, and
      evidences.
    """
    profile = inputs.get("profile_topos")
    flow_map = inputs.get("flow_map")
    nucleus_map = inputs.get("nucleus_map")
    flow_ev = inputs.get("flow_laws_evidence")
    nucleus_ev = inputs.get("nucleus_laws_evidence")
    comm_ev = inputs.get("commutation_evidence")
    if None in (profile, flow_map, nucleus_map, flow_ev, nucleus_ev, comm_ev):
        raise KeyError(
            "geometry_profile requires 'profile_topos', 'flow_map', 'nucleus_map', "
            "'flow_laws_evidence', 'nucleus_laws_evidence', and 'commutation_evidence' inputs"
        )

    if profile.get("kind") != "profile_topos":
        raise LawValidationError("geometry_profile profile_topos input must have kind 'profile_topos'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("geometry_profile flow_map input must have kind 'flow_map'")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("geometry_profile nucleus_map input must have kind 'nucleus_map'")
    if flow_ev.get("kind") != "flow_laws_evidence":
        raise LawValidationError("geometry_profile flow_laws_evidence input must have kind 'flow_laws_evidence'")
    if nucleus_ev.get("kind") != "nucleus_laws_evidence":
        raise LawValidationError("geometry_profile nucleus_laws_evidence input must have kind 'nucleus_laws_evidence'")
    if comm_ev.get("kind") != "commutation_evidence":
        raise LawValidationError("geometry_profile commutation_evidence input must have kind 'commutation_evidence'")

    profile_id = profile["id"]
    # Carrier and dimension coherence for FlowProfile and NucleateProfile.
    if flow_map.get("carrier_id") != profile_id or nucleus_map.get("carrier_id") != profile_id:
        raise LawValidationError("geometry_profile flow_map and nucleus_map must use profile_topos as carrier")
    elements = set(profile.get("elements", []))
    flow_elements = set(flow_map.get("elements", []))
    nucleus_elements = set(nucleus_map.get("elements", []))
    if elements != flow_elements or elements != nucleus_elements:
        raise LawValidationError(
            "geometry_profile flow_map/nucleus_map elements must coincide with profile_topos elements"
        )

    # Flow laws evidence: monotone/inflationary/distributive on the profile lattice.
    if flow_ev.get("status") != "pass":
        raise LawValidationError("geometry_profile requires flow_laws_evidence.status == 'pass'")
    if flow_ev.get("flow_id") != flow_map["id"] or flow_ev.get("carrier_id") != profile_id:
        raise LawValidationError(
            "geometry_profile flow_laws_evidence must reference the profile flow_map and profile_topos"
        )

    # Nucleus laws evidence: closure laws on the profile lattice.
    if nucleus_ev.get("status") != "pass":
        raise LawValidationError("geometry_profile requires nucleus_laws_evidence.status == 'pass'")
    if nucleus_ev.get("nucleus_id") != nucleus_map["id"] or nucleus_ev.get("carrier_id") != profile_id:
        raise LawValidationError(
            "geometry_profile nucleus_laws_evidence must reference the profile nucleus_map and profile_topos"
        )

    # Commutation evidence: F∘ν = ν∘F on the same lattice, covering all elements.
    if comm_ev.get("status") != "pass":
        raise LawValidationError("geometry_profile requires commutation_evidence.status == 'pass'")
    if (
        comm_ev.get("flow_id") != flow_map["id"]
        or comm_ev.get("nucleus_id") != nucleus_map["id"]
        or comm_ev.get("carrier_id") != profile_id
    ):
        raise LawValidationError(
            "geometry_profile commutation_evidence must reference the profile flow_map, nucleus_map, and profile_topos"
        )
    table = comm_ev.get("table") or []
    if {row.get("element") for row in table} != elements:
        raise LawValidationError(
            "geometry_profile commutation_evidence.table must cover exactly the profile_topos elements"
        )

    geometry = {
        "kind": "geometry_profile",
        "profile_topos_id": profile_id,
        "flow_map_id": flow_map["id"],
        "nucleus_map_id": nucleus_map["id"],
        "flow_laws_evidence_id": flow_ev["id"],
        "nucleus_laws_evidence_id": nucleus_ev["id"],
        "commutation_evidence_id": comm_ev["id"],
        "act_ref": "GeometryProfile",
    }
    ensure_id_coherence(geometry)

    edges = [
        {
            "operator": "geometry_profile",
            "src": profile_id,
            "tgt": geometry["id"],
        },
        {
            "operator": "geometry_profile",
            "src": flow_map["id"],
            "tgt": geometry["id"],
        },
        {
            "operator": "geometry_profile",
            "src": nucleus_map["id"],
            "tgt": geometry["id"],
        },
    ]

    return RealizerOutput(
        nodes=[geometry],
        edges=edges,
        bindings={"geometry_profile": geometry["id"]},
    )

