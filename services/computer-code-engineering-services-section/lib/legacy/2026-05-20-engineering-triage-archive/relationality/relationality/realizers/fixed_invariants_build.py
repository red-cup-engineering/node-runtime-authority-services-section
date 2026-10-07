from __future__ import annotations

from typing import Dict, List, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_lattice


def _restrict_order(order: Mapping[str, List[str]], subset: List[str]) -> Dict[str, List[str]]:
    subset_set = set(subset)
    return {
        x: [y for y in order.get(x, []) if y in subset_set]
        for x in subset
    }


def _restrict_table(table: Mapping[str, Mapping[str, str]], subset: List[str], name: str) -> Dict[str, Dict[str, str]]:
    subset_set = set(subset)
    restricted: Dict[str, Dict[str, str]] = {}
    for x in subset:
        row = table.get(x)
        if row is None:
            raise LawValidationError(f"fixed_invariants_build: {name} table missing row for {x!r}")
        new_row: Dict[str, str] = {}
        for y in subset:
            result = row.get(y)
            if result is None:
                raise LawValidationError(f"fixed_invariants_build: {name}({x!r},{y!r}) undefined")
            if result not in subset_set:
                raise LawValidationError(
                    f"fixed_invariants_build: {name}({x!r},{y!r}) = {result!r} not in fixed subset"
                )
            new_row[y] = result
        restricted[x] = new_row
    return restricted


def _restrict_negate(negate_map: Mapping[str, str], subset: List[str]) -> Dict[str, str]:
    subset_set = set(subset)
    restricted: Dict[str, str] = {}
    for x in subset:
        nx = negate_map.get(x)
        if nx is None:
            raise LawValidationError("fixed_invariants_build: negate_map missing entry for fixed element")
        if nx not in subset_set:
            raise LawValidationError(
                "fixed_invariants_build: negate_map maps fixed element outside fixed subset"
            )
        restricted[x] = nx
    return restricted


def _find_bounds_from_tables(elements: List[str], meet_table: Mapping[str, Mapping[str, str]], join_table: Mapping[str, Mapping[str, str]]) -> tuple[str, str]:
    elem_set = set(elements)
    bottom_candidates: List[str] = []
    top_candidates: List[str] = []

    for x in elements:
        # bottom: meet(x,y) = x for all y
        if all(meet_table[x][y] == x and meet_table[y][x] == x for y in elements):
            bottom_candidates.append(x)
        # top: join(x,y) = x for all y
        if all(join_table[x][y] == x and join_table[y][x] == x for y in elements):
            top_candidates.append(x)

    if not bottom_candidates or not top_candidates:
        raise LawValidationError(
            "fixed_invariants_build: could not identify bottom/top elements in fixed subset from meet/join tables"
        )
    # When multiple candidates exist, choose deterministically by string order.
    bottom = sorted(bottom_candidates)[0]
    top = sorted(top_candidates)[0]
    return bottom, top


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    fixed_invariants_build realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier encoding the full profile lattice.
    fixed_profile:
        FixedProfile carrier selecting a subset of profile recognitions.

    Semantics
    ---------
    Realizes FixedInvariant and its lattice refinements by restricting the
    profile lattice to the fixed_profile elements:

      - elements = fixed_profile.elements
      - order / meet / join / imply / negate are inherited from profile_topos
        but restricted to this subset, requiring closure.
      - bottom/top are computed from the restricted meet/join tables.

    Emits a fixed_invariants carrier.
    """
    profile = inputs.get("profile_topos")
    fixed_profile = inputs.get("fixed_profile")
    if profile is None or fixed_profile is None:
        raise KeyError("fixed_invariants_build requires 'profile_topos' and 'fixed_profile' inputs")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("fixed_invariants_build profile_topos input must have kind 'profile_topos'")
    if fixed_profile.get("kind") != "fixed_profile":
        raise LawValidationError("fixed_invariants_build fixed_profile input must have kind 'fixed_profile'")

    if fixed_profile.get("profile_topos_id") != profile.get("id"):
        raise LawValidationError(
            "fixed_invariants_build requires fixed_profile.profile_topos_id to match profile_topos.id"
        )

    profile_elements: List[str] = list(profile.get("elements", []))
    subset: List[str] = list(fixed_profile.get("elements", []))
    subset_set = set(subset)
    if not subset or not subset_set.issubset(set(profile_elements)):
        raise LawValidationError(
            "fixed_invariants_build requires fixed_profile.elements to be a non-empty subset of profile_topos.elements"
        )

    order = profile.get("order") or {}
    meet_table = profile.get("meet_table") or {}
    join_table = profile.get("join_table") or {}
    imply_table = profile.get("imply_table") or {}
    negate_map = profile.get("negate_map") or {}

    restricted_order = _restrict_order(order, subset)
    restricted_meet = _restrict_table(meet_table, subset, "meet")
    restricted_join = _restrict_table(join_table, subset, "join")
    restricted_imply = _restrict_table(imply_table, subset, "imply")
    restricted_negate = _restrict_negate(negate_map, subset)
    bottom, top = _find_bounds_from_tables(subset, restricted_meet, restricted_join)

    fixed_invariants = {
        "kind": "fixed_invariants",
        "elements": subset,
        "order": restricted_order,
        "meet_table": restricted_meet,
        "join_table": restricted_join,
        "imply_table": restricted_imply,
        "negate_map": restricted_negate,
        "bottom": bottom,
        "top": top,
    }
    # Enforce lattice laws on the restricted carrier.
    validate_lattice(fixed_invariants)
    ensure_id_coherence(fixed_invariants)

    edge = {
        "operator": "fixed_invariants_build",
        "src": fixed_profile["id"],
        "tgt": fixed_invariants["id"],
    }

    return RealizerOutput(
        nodes=[fixed_invariants],
        edges=[edge],
        bindings={"fixed_invariants": fixed_invariants["id"]},
    )

