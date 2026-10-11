from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_integral realizer.

    Inputs
    ------
    comonad_derivative:
        ComonadDerivative carrier acting on fixed invariants.
    fixed_invariants:
        FixedInvariants carrier providing the fixed profile lattice.
    nucleus_map:
        NucleusMap carrier whose carrier lattice contains the fixed invariants.

    Semantics
    ---------
    ProfileIntegral = (FixedNucleateProfile ComonadDerivative) integrates the
    derivative along the fixed nucleus. Concretely, we compute:

        I(x) = ν(D(x))

    restricted to fixed_invariants.elements, yielding a FixedOperator-valued
    carrier representing the integrated dynamics over the fixed profile.
    """
    derivative = inputs.get("comonad_derivative")
    fixed_invariants = inputs.get("fixed_invariants")
    nucleus_map = inputs.get("nucleus_map")
    if derivative is None or fixed_invariants is None or nucleus_map is None:
        raise KeyError(
            "profile_integral requires 'comonad_derivative', 'fixed_invariants', and 'nucleus_map' inputs"
        )
    if derivative.get("kind") != "comonad_derivative":
        raise LawValidationError("profile_integral comonad_derivative input must have kind 'comonad_derivative'")
    if fixed_invariants.get("kind") != "fixed_invariants":
        raise LawValidationError("profile_integral fixed_invariants input must have kind 'fixed_invariants'")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("profile_integral nucleus_map input must have kind 'nucleus_map'")

    elements = set(derivative.get("elements", []))
    fixed_elements = set(fixed_invariants.get("elements", []))
    if elements != fixed_elements:
        raise LawValidationError(
            "profile_integral requires comonad_derivative.elements to equal fixed_invariants.elements"
        )
    nucleus_elements = set(nucleus_map.get("elements", []))
    if not elements.issubset(nucleus_elements):
        raise LawValidationError(
            "profile_integral requires fixed_invariants.elements to be a subset of nucleus_map.elements"
        )

    deriv_table = derivative.get("derivative_table") or {}
    nu_table = nucleus_map.get("nucleus_table") or {}
    integral_table: Dict[str, str] = {}
    for src in elements:
        if src not in deriv_table:
            raise LawValidationError("comonad_derivative.derivative_table must be total on its elements")
        image = deriv_table[src]
        if image not in nucleus_elements:
            raise LawValidationError(
                f"comonad_derivative.derivative_table maps {src!r} to {image!r} outside nucleus carrier"
            )
        closed = nu_table.get(image)
        if closed is None:
            raise LawValidationError(
                "nucleus_map.nucleus_table must be total on its elements"
            )
        if closed not in elements:
            raise LawValidationError(
                "profile_integral requires ν(D(x)) to lie in fixed invariants for all x"
            )
        integral_table[src] = closed

    integral_operator = {
        "kind": "fixed_operator",
        "carrier_id": fixed_invariants["id"],
        "elements": list(elements),
        "operator_table": integral_table,
        "act_ref": "ProfileIntegral",
    }
    ensure_id_coherence(integral_operator)

    edges = [
        {
            "operator": "profile_integral",
            "src": derivative["id"],
            "tgt": integral_operator["id"],
        },
        {
            "operator": "profile_integral",
            "src": fixed_invariants["id"],
            "tgt": integral_operator["id"],
        },
        {
            "operator": "profile_integral",
            "src": nucleus_map["id"],
            "tgt": integral_operator["id"],
        },
    ]

    return RealizerOutput(
        nodes=[integral_operator],
        edges=edges,
        bindings={"fixed_operator": integral_operator["id"]},
    )

