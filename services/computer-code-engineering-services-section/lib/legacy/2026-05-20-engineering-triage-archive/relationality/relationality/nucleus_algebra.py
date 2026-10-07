from __future__ import annotations

"""
Pure nucleus algebra utilities.

These helpers centralize the finite-lattice nucleus laws and iteration
semantics so realizers and validators do not duplicate the algebra.  They
operate purely on payload dictionaries and raise ``LawValidationError`` on
structural or algebraic violations, never mutating inputs.
"""

from typing import Dict, Iterable, Mapping, Tuple

from .validation import LawValidationError


def resolve_nucleus_carrier(graph: object, nucleus_map: Mapping[str, object]) -> Mapping[str, object]:
    """
    Resolve the carrier for a nucleus_map from a graph-like object.

    The carrier must be present in ``graph.nodes`` and provide a lattice
    structure (elements/states, order, meet_table, join_table).
    """
    carrier_id = nucleus_map.get("carrier_id")
    if not isinstance(carrier_id, str):
        raise LawValidationError("nucleus_map must declare a string carrier_id")
    carrier = getattr(graph, "nodes", {}).get(carrier_id)
    if carrier is None:
        raise LawValidationError(f"carrier {carrier_id} referenced by nucleus_map not found in graph")
    elements_key = "elements" if "elements" in carrier else "states"
    required = {elements_key, "order", "meet_table", "join_table"}
    if not required.issubset(carrier.keys()):
        raise LawValidationError(
            "nucleus carrier must provide elements/states, order, meet_table, and join_table"
        )
    return carrier


def _carrier_elements(carrier: Mapping[str, object]) -> Tuple[str, Dict[str, None]]:
    elements_key = "elements" if "elements" in carrier else "states"
    elements = list(carrier[elements_key])
    return elements_key, {e: None for e in elements}


def _require_total_table(table: Mapping[str, str], elements: Iterable[str], name: str) -> None:
    element_set = set(elements)
    if set(table.keys()) != element_set:
        raise LawValidationError(f"{name} table must have an entry for every element")
    for src, tgt in table.items():
        if tgt not in element_set:
            raise LawValidationError(f"{name} maps {src} to unknown element {tgt}")


def nucleus_law_checks(
    carrier: Mapping[str, object],
    nucleus_map: Mapping[str, object],
) -> Tuple[Dict[str, bool], Dict[str, object] | None]:
    """
    Evaluate nucleus laws against a carrier lattice and nucleus_map.

    Returns (checks, counterexample) where checks enumerates the five laws
    and counterexample is the first failing witness or ``None``.
    """
    elements_key, carrier_elements = _carrier_elements(carrier)
    carrier_element_set = set(carrier_elements.keys())
    nucleus_elements = set(nucleus_map.get("elements") or [])
    if carrier_element_set != nucleus_elements:
        raise LawValidationError("nucleus_map elements must match carrier elements exactly")
    nucleus_table = nucleus_map.get("nucleus_table") or {}
    _require_total_table(nucleus_table, carrier_element_set, "nucleus_table")
    order = carrier["order"]
    meet_table = carrier["meet_table"]
    join_table = carrier["join_table"]

    def leq(a: str, b: str) -> bool:
        return b in order.get(a, [])

    checks = {
        "extensive": True,
        "idempotent": True,
        "monotone": True,
        "equalize": True,
        "absorb": True,
    }
    counterexample: Dict[str, object] | None = None

    def record(law: str, details: Mapping[str, object]) -> None:
        nonlocal counterexample
        checks[law] = False
        if counterexample is None:
            ce = {"law": law}
            ce.update(details)
            counterexample = dict(ce)

    # Extensive: x <= ν(x)
    for x in carrier_element_set:
        nu_x = nucleus_table[x]
        if not leq(x, nu_x):
            record("extensive", {"x": x, "nu_x": nu_x})
            break

    # Idempotent: ν(ν(x)) = ν(x)
    for x in carrier_element_set:
        nu_x = nucleus_table[x]
        nu_nu_x = nucleus_table[nu_x]
        if nu_nu_x != nu_x:
            record("idempotent", {"x": x, "nu_x": nu_x, "nu_nu_x": nu_nu_x})
            break

    # Monotone: x <= y ⇒ ν(x) <= ν(y)
    if checks["monotone"]:
        for x in carrier_element_set:
            nu_x = nucleus_table[x]
            for y in order.get(x, []):
                nu_y = nucleus_table[y]
                if not leq(nu_x, nu_y):
                    record("monotone", {"x": x, "y": y, "nu_x": nu_x, "nu_y": nu_y})
                    break
            if not checks["monotone"]:
                break

    # Equalize: ν(x ∧ ν(y)) = ν(x ∧ y) and ν(ν(x) ∨ y) = ν(x ∨ y)
    if checks["equalize"]:
        for x in carrier_element_set:
            for y in carrier_element_set:
                nu_y = nucleus_table[y]
                meet_x_y = meet_table[x][y]
                meet_x_nu_y = meet_table[x][nu_y]
                left_meet = nucleus_table[meet_x_nu_y]
                right_meet = nucleus_table[meet_x_y]
                if left_meet != right_meet:
                    record(
                        "equalize",
                        {"mode": "meet", "x": x, "y": y, "lhs": left_meet, "rhs": right_meet},
                    )
                    break
                nu_x = nucleus_table[x]
                join_x_y = join_table[x][y]
                join_nu_x_y = join_table[nu_x][y]
                left_join = nucleus_table[join_nu_x_y]
                right_join = nucleus_table[join_x_y]
                if left_join != right_join:
                    record(
                        "equalize",
                        {"mode": "join", "x": x, "y": y, "lhs": left_join, "rhs": right_join},
                    )
                    break
            if not checks["equalize"]:
                break

    # Absorb: x ∧ ν(y) <= ν(x ∧ y)
    if checks["absorb"]:
        for x in carrier_element_set:
            for y in carrier_element_set:
                nu_y = nucleus_table[y]
                left = meet_table[x][nu_y]
                meet_x_y = meet_table[x][y]
                right = nucleus_table[meet_x_y]
                if not leq(left, right):
                    record("absorb", {"x": x, "y": y, "left": left, "right": right})
                    break
            if not checks["absorb"]:
                break

    return checks, counterexample


def apply_nucleus(nucleus_map: Mapping[str, object], element: str) -> str:
    """
    Apply a nucleus_map to a single element, enforcing totality on its basis.
    """
    elements = set(nucleus_map.get("elements") or [])
    table = nucleus_map.get("nucleus_table") or {}
    if element not in table:
        raise LawValidationError("nucleus_table must contain every element of the carrier")
    target = table[element]
    if target not in elements:
        raise LawValidationError(f"nucleus_table maps {element} outside the carrier")
    return target


def iterate_nucleus(nucleus_map: Mapping[str, object], start: str) -> Tuple[str, list[str], int]:
    """
    Iterate a nucleus starting from ``start`` until a fixed point is reached.

    Returns (fixed_point, path, iteration_count). Raises LawValidationError
    if the iteration leaves the carrier or enters a non-trivial cycle.
    """
    elements = set(nucleus_map.get("elements") or [])
    table = nucleus_map.get("nucleus_table") or {}
    if set(table.keys()) != elements:
        raise LawValidationError("nucleus_table must be total on its elements")
    if start not in elements:
        raise LawValidationError("start element must lie in the nucleus carrier")
    path = [start]
    seen = {start}
    current = start
    iterations = 0
    while True:
        nxt = table[current]
        iterations += 1
        path.append(nxt)
        if nxt not in elements:
            raise LawValidationError(f"nucleus iteration mapped {current} to unknown element {nxt}")
        if nxt == current:
            return nxt, path, iterations
        if nxt in seen:
            raise LawValidationError("nucleus iteration entered a cycle without reaching a fixed point")
        seen.add(nxt)
        current = nxt
