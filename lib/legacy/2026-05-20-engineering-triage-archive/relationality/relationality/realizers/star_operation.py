from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    star_operation realizer.

    Inputs
    ------
    fixed_operator:
        FixedOperator carrier whose operator_table acts on fixed invariants.
    fixed_invariants:
        FixedInvariants carrier providing the fixed profile lattice.
    nucleus_map:
        NucleusMap carrier whose carrier lattice contains the fixed invariants.

    Semantics
    ---------
    StarOperation = (FixedNucleateProfile FixedOperator) collapses the operator
    via the fixed nucleus. Concretely, we compute a new operator_table by
    applying the nucleus_map to the image of each element:

        F*(x) = ν(F(x))

    restricted to fixed_invariants.elements. On systems where fixed invariants
    are actual fixed points of ν, this is an idempotent refinement of the
    original operator.
    """
    fixed_operator = inputs.get("fixed_operator")
    fixed_invariants = inputs.get("fixed_invariants")
    nucleus_map = inputs.get("nucleus_map")
    if fixed_operator is None or fixed_invariants is None or nucleus_map is None:
        raise KeyError("star_operation requires 'fixed_operator', 'fixed_invariants', and 'nucleus_map' inputs")
    if fixed_operator.get("kind") != "fixed_operator":
        raise LawValidationError("star_operation fixed_operator input must have kind 'fixed_operator'")
    if fixed_invariants.get("kind") != "fixed_invariants":
        raise LawValidationError("star_operation fixed_invariants input must have kind 'fixed_invariants'")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("star_operation nucleus_map input must have kind 'nucleus_map'")

    elements = set(fixed_operator.get("elements", []))
    fixed_elements = set(fixed_invariants.get("elements", []))
    if elements != fixed_elements:
        raise LawValidationError(
            "star_operation requires fixed_operator.elements to equal fixed_invariants.elements"
        )
    nucleus_elements = set(nucleus_map.get("elements", []))
    if not elements.issubset(nucleus_elements):
        raise LawValidationError(
            "star_operation requires fixed_invariants.elements to be a subset of nucleus_map.elements"
        )

    op_table = fixed_operator.get("operator_table") or {}
    nu_table = nucleus_map.get("nucleus_table") or {}
    star_table: Dict[str, str] = {}
    for src in elements:
        if src not in op_table:
            raise LawValidationError("fixed_operator.operator_table must be total on its elements")
        image = op_table[src]
        if image not in nucleus_elements:
            raise LawValidationError(
                f"fixed_operator.operator_table maps {src!r} to {image!r} outside nucleus carrier"
            )
        closed = nu_table.get(image)
        if closed is None:
            raise LawValidationError(
                "nucleus_map.nucleus_table must be total on its elements"
            )
        if closed not in elements:
            raise LawValidationError(
                "star_operation requires ν(F(x)) to lie in fixed invariants for all x"
            )
        star_table[src] = closed

    new_operator = {
        "kind": "fixed_operator",
        "carrier_id": fixed_invariants["id"],
        "elements": list(elements),
        "operator_table": star_table,
        "act_ref": "StarOperation",
    }
    ensure_id_coherence(new_operator)

    edges = [
        {
            "operator": "star_operation",
            "src": fixed_operator["id"],
            "tgt": new_operator["id"],
        },
        {
            "operator": "star_operation",
            "src": fixed_invariants["id"],
            "tgt": new_operator["id"],
        },
        {
            "operator": "star_operation",
            "src": nucleus_map["id"],
            "tgt": new_operator["id"],
        },
    ]

    return RealizerOutput(
        nodes=[new_operator],
        edges=edges,
        bindings={"fixed_operator": new_operator["id"]},
    )

