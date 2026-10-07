from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _load_carrier(graph, flow_map: dict) -> dict:
    carrier_id = flow_map.get("carrier_id")
    if not isinstance(carrier_id, str):
        raise LawValidationError("flow_map must declare a carrier_id")
    carrier = graph.nodes.get(carrier_id)
    if carrier is None:
        raise KeyError(f"carrier {carrier_id} referenced by flow_map not found in graph")
    # Flow laws require a lattice carrier with explicit order and meet
    # table. The carrier may present its lattice elements either as
    # ``elements`` (profile_topos, fixed_invariants) or as ``states``
    # (phase_space); both are accepted.
    elements_key = "elements" if "elements" in carrier else "states"
    if elements_key not in carrier or "order" not in carrier or "meet_table" not in carrier:
        raise LawValidationError(
            "flow_laws_check carrier must provide elements/states, order, and meet_table"
        )
    return carrier


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    flow_laws_check realizer.

    Input
    -----
    flow_map:
        Carrier encoding a flow table F:R→R over a finite lattice carrier.

    Semantics
    ---------
    Evaluate the flow laws over the finite carrier:
    - monotone:      x <= y ⇒ F(x) <= F(y)
    - inflationary:  x <= F(x)
    - distributive:  F(x ∧ y) <= F(x) ∧ F(y)

    Produce a flow_laws_evidence node recording per-law booleans and the first
    counterexample (if any). This is diagnostic: law failures are encoded in
    the evidence rather than raised.
    """
    flow_map = inputs.get("flow_map")
    if flow_map is None:
        raise KeyError("flow_laws_check requires flow_map input")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("flow_laws_check flow_map input must have kind 'flow_map'")

    carrier = _load_carrier(graph, flow_map)

    elements_key = "elements" if "elements" in carrier else "states"
    carrier_elements: List[str] = list(carrier[elements_key])
    carrier_element_set = set(carrier_elements)
    flow_elements = set(flow_map["elements"])
    if carrier_element_set != flow_elements:
        raise LawValidationError("flow_map elements must match carrier elements exactly")

    order = carrier["order"]
    meet_table = carrier["meet_table"]
    flow_table = flow_map["flow_table"]

    def leq(a: str, b: str) -> bool:
        return b in order.get(a, [])

    checks = {
        "monotone": True,
        "inflationary": True,
        "distributive": True,
    }
    counterexample = None

    def record(law: str, details: dict) -> None:
        nonlocal counterexample
        checks[law] = False
        if counterexample is None:
            ce = {"law": law}
            ce.update(details)
            counterexample = ce

    # Monotone: x <= y ⇒ F(x) <= F(y)
    for x in carrier_elements:
        fx = flow_table[x]
        for y in order.get(x, []):
            fy = flow_table[y]
            if not leq(fx, fy):
                record("monotone", {"x": x, "y": y, "fx": fx, "fy": fy})
                break
        if not checks["monotone"]:
            break

    # Inflationary: x <= F(x)
    if checks["inflationary"]:
        for x in carrier_elements:
            fx = flow_table[x]
            if not leq(x, fx):
                record("inflationary", {"x": x, "fx": fx})
                break

    # Distributive inequality: F(x ∧ y) <= F(x) ∧ F(y)
    if checks["distributive"]:
        for x in carrier_elements:
            for y in carrier_elements:
                meet_xy = meet_table[x][y]
                f_meet = flow_table[meet_xy]
                fx = flow_table[x]
                fy = flow_table[y]
                meet_fx_fy = meet_table[fx][fy]
                if not leq(f_meet, meet_fx_fy):
                    record(
                        "distributive",
                        {
                            "x": x,
                            "y": y,
                            "meet_xy": meet_xy,
                            "f_meet": f_meet,
                            "fx": fx,
                            "fy": fy,
                            "meet_fx_fy": meet_fx_fy,
                        },
                    )
                    break
            if not checks["distributive"]:
                break

    status = "pass" if all(checks.values()) else "fail"

    evidence = {
        "kind": "flow_laws_evidence",
        "flow_id": flow_map["id"],
        "carrier_id": carrier["id"],
        "checks": checks,
        "status": status,
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "flow_laws_check",
            "src": flow_map["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "flow_laws_check",
            "src": carrier["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"flow_laws_evidence": evidence["id"]},
    )
