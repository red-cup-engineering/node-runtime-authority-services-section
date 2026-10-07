from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    fixed_finite_limits_build realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier encoding the full profile lattice, including
        finite_limits data.
    fixed_invariants:
        FixedInvariants carrier providing the fixed invariant lattice.

    Semantics
    ---------
    Realizes FixedFiniteLimits = (ProfileFiniteLimits FixedInvariantLattice)
    by restricting finite limits to the fixed invariant lattice:

    - terminal is taken to be fixed_invariants.top;
    - binary products are computed in the poset category of the fixed lattice
      via meets:

          prod(a, b) = meet(a, b)

      for all a, b in fixed_invariants.elements, encoded under canonical
      keys "a|b" with (a, b) sorted lexicographically.

    Emits a fixed_finite_limits carrier.
    """
    profile = inputs.get("profile_topos")
    fixed_invariants = inputs.get("fixed_invariants")
    if profile is None or fixed_invariants is None:
        raise KeyError("fixed_finite_limits_build requires 'profile_topos' and 'fixed_invariants' inputs")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("fixed_finite_limits_build profile_topos input must have kind 'profile_topos'")
    if fixed_invariants.get("kind") != "fixed_invariants":
        raise LawValidationError("fixed_finite_limits_build fixed_invariants input must have kind 'fixed_invariants'")

    profile_elements = set(profile.get("elements", []))
    fixed_elements = list(fixed_invariants.get("elements", []))
    if not fixed_elements:
        raise LawValidationError("fixed_finite_limits_build requires non-empty fixed_invariants.elements")
    if not set(fixed_elements).issubset(profile_elements):
        raise LawValidationError(
            "fixed_finite_limits_build requires fixed_invariants.elements to be a subset of profile_topos.elements"
        )

    meet_table = fixed_invariants.get("meet_table") or {}
    # Validate that the meet table is total on the fixed lattice; the global
    # lattice laws have already been enforced by validate_object on
    # fixed_invariants, so here we only ensure totality for our construction.
    fixed_set = set(fixed_elements)
    for a in fixed_elements:
        row = meet_table.get(a)
        if row is None or set(row.keys()) != fixed_set:
            raise LawValidationError("fixed_finite_limits_build requires meet_table to be total on fixed elements")
        for b, m in row.items():
            if m not in fixed_set:
                raise LawValidationError(
                    f"fixed_finite_limits_build: meet({a!r},{b!r}) = {m!r} not in fixed_invariants.elements"
                )

    products: Dict[str, str] = {}
    for a in fixed_elements:
        for b in fixed_elements:
            key_a, key_b = sorted((a, b))
            key = f"{key_a}|{key_b}"
            # Use meet as the categorical product in the poset view.
            products[key] = meet_table[a][b]

    payload = {
        "kind": "fixed_finite_limits",
        "fixed_invariants_id": fixed_invariants["id"],
        "terminal": fixed_invariants["top"],
        "products": products,
        "act_ref": "FixedFiniteLimits",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "fixed_finite_limits_build",
            "src": fixed_invariants["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "fixed_finite_limits_build",
            "src": profile["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"fixed_finite_limits": payload["id"]},
    )

