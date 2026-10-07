from __future__ import annotations

import copy
from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.nucleus_algebra import iterate_nucleus
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    nucleus_map = inputs.get("nucleus_map")
    phase_space = inputs.get("phase_space")
    if nucleus_map is None or phase_space is None:
        raise KeyError("fix_nucleus requires nucleus_map and phase_space inputs")
    states = set(phase_space["states"])
    nucleus_elements = set(nucleus_map["elements"])
    if not states.issubset(nucleus_elements):
        raise LawValidationError("phase_space states must be contained in nucleus_map elements")
    current = phase_space["current_state"]
    if current not in states:
        raise LawValidationError("current_state not in phase_space states")
    fixed_point, path, iteration_count = iterate_nucleus(nucleus_map, current)
    new_phase_space = copy.deepcopy(phase_space)
    new_phase_space["current_state"] = fixed_point
    new_phase_space.pop("id", None)
    ensure_id_coherence(new_phase_space)
    last_states = path[-2:] if len(path) >= 2 else [path[-1]]
    evidence = {
        "kind": "fix_nucleus_iteration_evidence",
        "nucleus_id": nucleus_map["id"],
        "carrier_id": phase_space["id"],
        "start_element": path[0],
        "iteration_count": iteration_count,
        "last_states": last_states,
        "status": "pass",
    }
    ensure_id_coherence(evidence)
    edges = [
        {
            "operator": "fix_nucleus",
            "src": phase_space["id"],
            "tgt": new_phase_space["id"],
        },
        {
            "operator": "fix_nucleus",
            "src": nucleus_map["id"],
            "tgt": evidence["id"],
        },
    ]
    return RealizerOutput(
        nodes=[new_phase_space, evidence],
        edges=edges,
        bindings={"phase_space": new_phase_space["id"], "fix_nucleus_iteration_evidence": evidence["id"]},
    )
