from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    fixed_dynamics_build realizer.

    Inputs
    ------
    flow_map:
        FlowMap carrier encoding F:R→R on a finite lattice.
    fixed_invariants:
        FixedInvariants carrier providing the fixed invariant lattice.

    Semantics
    ---------
    Realizes FixedDynamics = (ProfileDynamics FixedPhaseSpace) by restricting
    the profile dynamics (flow_map) to the fixed invariant lattice:

    - requires fixed_invariants.elements ⊆ flow_map.elements;
    - constructs an operator_table on fixed_invariants.elements via
          D(x) = F(x)
      and requires D(x) ∈ fixed_invariants.elements for all x.

    Emits a fixed_operator carrier representing the fixed dynamics.
    """
    flow_map = inputs.get("flow_map")
    fixed_invariants = inputs.get("fixed_invariants")
    if flow_map is None or fixed_invariants is None:
        raise KeyError("fixed_dynamics_build requires 'flow_map' and 'fixed_invariants' inputs")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("fixed_dynamics_build flow_map input must have kind 'flow_map'")
    if fixed_invariants.get("kind") != "fixed_invariants":
        raise LawValidationError("fixed_dynamics_build fixed_invariants input must have kind 'fixed_invariants'")

    flow_elements = set(flow_map.get("elements", []))
    fixed_elements = list(fixed_invariants.get("elements", []))
    if not fixed_elements:
        raise LawValidationError("fixed_dynamics_build requires non-empty fixed_invariants.elements")
    if not set(fixed_elements).issubset(flow_elements):
        raise LawValidationError(
            "fixed_dynamics_build requires fixed_invariants.elements to be a subset of flow_map.elements"
        )

    flow_table = flow_map.get("flow_table") or {}
    dynamics_table: Dict[str, str] = {}
    fixed_set = set(fixed_elements)
    for x in fixed_elements:
        image = flow_table.get(x)
        if image is None:
            raise LawValidationError(f"fixed_dynamics_build: flow_table missing image for {x!r}")
        if image not in fixed_set:
            raise LawValidationError(
                f"fixed_dynamics_build: flow_table maps {x!r} to {image!r} outside fixed_invariants.elements"
            )
        dynamics_table[x] = image

    payload = {
        "kind": "fixed_operator",
        "carrier_id": fixed_invariants["id"],
        "elements": fixed_elements,
        "operator_table": dynamics_table,
        "act_ref": "FixedDynamics",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "fixed_dynamics_build",
            "src": flow_map["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "fixed_dynamics_build",
            "src": fixed_invariants["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"fixed_dynamics": payload["id"]},
    )

