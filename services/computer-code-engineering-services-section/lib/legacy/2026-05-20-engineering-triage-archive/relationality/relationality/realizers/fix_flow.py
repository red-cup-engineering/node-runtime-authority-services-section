from __future__ import annotations

import copy
from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    flow_map = inputs.get("flow_map")
    phase_space = inputs.get("phase_space")
    if flow_map is None or phase_space is None:
        raise KeyError("fix_flow requires flow_map and phase_space inputs")
    states = set(phase_space["states"])
    flow_elements = set(flow_map["elements"])
    if not states.issubset(flow_elements):
        raise LawValidationError("phase_space states must be contained in flow_map elements")
    flow_table = flow_map["flow_table"]
    for state in states:
        if state not in flow_table:
            raise LawValidationError(f"flow_table missing entry for state {state}")
        if flow_table[state] not in flow_elements:
            raise LawValidationError(f"flow_table maps {state} outside carrier")
    current = phase_space["current_state"]
    if current not in states:
        raise LawValidationError("current_state not in phase_space states")
    path = [current]
    seen = {current}
    iteration_count = 0
    while True:
        nxt = flow_table[current]
        iteration_count += 1
        path.append(nxt)
        if nxt == current:
            break
        if nxt in seen:
            # We have entered a non-trivial cycle; FixFlow is not earned.
            raise LawValidationError("flow iteration entered a cycle without reaching a fixed point")
        seen.add(nxt)
        current = nxt
    fixed_point = path[-1]
    new_phase_space = copy.deepcopy(phase_space)
    new_phase_space["current_state"] = fixed_point
    new_phase_space.pop("id", None)
    ensure_id_coherence(new_phase_space)
    last_states = path[-2:] if len(path) >= 2 else [path[-1]]
    evidence = {
        "kind": "fix_flow_iteration_evidence",
        "flow_id": flow_map["id"],
        "carrier_id": phase_space["id"],
        "start_element": path[0],
        "iteration_count": iteration_count,
        "last_states": last_states,
        "status": "pass",
    }
    ensure_id_coherence(evidence)
    edges = [
        {
            "operator": "fix_flow",
            "src": phase_space["id"],
            "tgt": new_phase_space["id"],
        },
        {
            "operator": "fix_flow",
            "src": flow_map["id"],
            "tgt": evidence["id"],
        },
    ]
    return RealizerOutput(
        nodes=[new_phase_space, evidence],
        edges=edges,
        bindings={"phase_space": new_phase_space["id"], "fix_flow_iteration_evidence": evidence["id"]},
    )
