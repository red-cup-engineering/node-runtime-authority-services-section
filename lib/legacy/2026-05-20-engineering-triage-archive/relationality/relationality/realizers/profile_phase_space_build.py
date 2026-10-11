from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_phase_space_build realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the recognition lattice.
    fixed_invariants:
        FixedInvariants carrier providing the fixed invariant lattice.

    Semantics
    ---------
    Realizes ProfilePhaseSpace at the carrier level by constructing a
    phase_space object whose state lattice coincides with the profile lattice
    and whose current_state is chosen from the fixed invariants:

        states = profile_topos.elements
        order / meet / join / imply / negate / bottom / top = profile_topos tables
        current_state = fixed_invariants.bottom

    This matches the System law that phase_space.states == profile_topos.elements
    and phase_space.current_state lies in the fixed invariants lattice.
    """
    profile = inputs.get("profile_topos")
    fixed_invariants = inputs.get("fixed_invariants")
    if profile is None or fixed_invariants is None:
        raise KeyError("profile_phase_space_build requires 'profile_topos' and 'fixed_invariants' inputs")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("profile_phase_space_build profile_topos input must have kind 'profile_topos'")
    if fixed_invariants.get("kind") != "fixed_invariants":
        raise LawValidationError("profile_phase_space_build fixed_invariants input must have kind 'fixed_invariants'")

    profile_elements: List[str] = list(profile.get("elements", []))
    if not profile_elements:
        raise LawValidationError("profile_phase_space_build requires non-empty profile_topos.elements")
    if not set(fixed_invariants.get("elements", [])).issubset(set(profile_elements)):
        raise LawValidationError(
            "profile_phase_space_build requires fixed_invariants.elements to be a subset of profile_topos.elements"
        )

    # Choose the bottom of the fixed invariants lattice as the current_state.
    current_state = fixed_invariants.get("bottom")
    if current_state not in set(fixed_invariants.get("elements", [])):
        raise LawValidationError(
            "profile_phase_space_build requires fixed_invariants.bottom to be an element of fixed_invariants.elements"
        )

    phase_space = {
        "kind": "phase_space",
        "states": profile_elements,
        "order": profile.get("order") or {},
        "meet_table": profile.get("meet_table") or {},
        "join_table": profile.get("join_table") or {},
        "imply_table": profile.get("imply_table") or {},
        "negate_map": profile.get("negate_map") or {},
        "bottom": profile.get("bottom"),
        "top": profile.get("top"),
        "current_state": current_state,
        "flow_tags": ["profile_flow"],
    }
    ensure_id_coherence(phase_space)

    edges = [
        {
            "operator": "profile_phase_space_build",
            "src": profile["id"],
            "tgt": phase_space["id"],
        },
        {
            "operator": "profile_phase_space_build",
            "src": fixed_invariants["id"],
            "tgt": phase_space["id"],
        },
    ]

    return RealizerOutput(
        nodes=[phase_space],
        edges=edges,
        bindings={"phase_space": phase_space["id"]},
    )
