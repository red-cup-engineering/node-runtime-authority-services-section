from __future__ import annotations

import copy
from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    fix_flow_nucleus realizer.

    Inputs
    ------
    flow_map:
        FlowMap carrier encoding F:R→R on a finite lattice.
    nucleus_map:
        NucleusMap carrier encoding ν:R→R on the same lattice.
    phase_space:
        PhaseSpace whose current_state is iterated under F∘ν.
    commutation_evidence:
        CommutationEvidence node witnessing F∘ν = ν∘F on the carrier.

    Semantics
    ---------
    Run a finite Flow–Nucleus iteration on the phase_space.current_state:

    - repeatedly apply F then ν, recording the visited states;
    - require that the supplied commutation_evidence certifies
      F∘ν = ν∘F on the carrier;
    - stop exactly when the new state is fixed by both F and ν;
    - reject any non-trivial cycle (no fixed point reached);
    - emit:
        * an updated phase_space with the fixed current_state;
        * fix_flow_nucleus_iteration_evidence recording flow/nucleus IDs,
          carrier_id, start_element, iteration_count, last_states and the
          commutation_evidence_id.
    """
    flow_map = inputs.get("flow_map")
    nucleus_map = inputs.get("nucleus_map")
    phase_space = inputs.get("phase_space")
    commutation_evidence = inputs.get("commutation_evidence")
    if flow_map is None or nucleus_map is None or phase_space is None or commutation_evidence is None:
        raise KeyError("fix_flow_nucleus requires flow_map, nucleus_map, phase_space, and commutation_evidence inputs")
    states = set(phase_space["states"])
    flow_elements = set(flow_map["elements"])
    nucleus_elements = set(nucleus_map["elements"])
    if flow_elements != nucleus_elements or not states.issubset(flow_elements):
        raise LawValidationError("flow_map and nucleus_map must share a carrier containing the phase_space states")
    flow_table = flow_map["flow_table"]
    nucleus_table = nucleus_map["nucleus_table"]
    # Require that the supplied commutation evidence already certifies F∘ν=ν∘F.
    if commutation_evidence.get("flow_id") != flow_map["id"] or commutation_evidence.get("nucleus_id") != nucleus_map["id"]:
        raise LawValidationError("commutation_evidence must reference the supplied flow_map and nucleus_map")
    if commutation_evidence.get("status") != "pass":
        raise LawValidationError("fix_flow_nucleus requires commuting flow/nucleus maps (commutation_evidence.status must be 'pass')")

    current = phase_space["current_state"]
    if current not in states:
        raise LawValidationError("current_state not in phase_space states")
    path: List[str] = [current]
    seen = {current}
    iteration_count = 0
    while True:
        # Apply F then ν as in the specification.
        after_flow = flow_table[current]
        after_nucleus = nucleus_table[after_flow]
        iteration_count += 1
        path.append(after_nucleus)
        # Fixed by both F and ν at the new point.
        if flow_table[after_nucleus] == after_nucleus and nucleus_table[after_nucleus] == after_nucleus:
            current = after_nucleus
            break
        if after_nucleus in seen:
            raise LawValidationError("fix_flow_nucleus iteration entered a cycle without reaching a commuting fixed point")
        seen.add(after_nucleus)
        current = after_nucleus
    fixed_point = current
    new_phase_space = copy.deepcopy(phase_space)
    new_phase_space["current_state"] = fixed_point
    new_phase_space.pop("id", None)
    ensure_id_coherence(new_phase_space)
    last_states = path[-2:] if len(path) >= 2 else [path[-1]]
    iteration_evidence = {
        "kind": "fix_flow_nucleus_iteration_evidence",
        "flow_id": flow_map["id"],
        "nucleus_id": nucleus_map["id"],
        "carrier_id": phase_space["id"],
        "start_element": path[0],
        "iteration_count": iteration_count,
        "last_states": last_states,
        "commutation_evidence_id": commutation_evidence["id"],
        "status": "pass",
    }
    ensure_id_coherence(iteration_evidence)
    edges = [
        {
            "operator": "fix_flow_nucleus",
            "src": phase_space["id"],
            "tgt": new_phase_space["id"],
        },
        {
            "operator": "fix_flow_nucleus",
            "src": flow_map["id"],
            "tgt": iteration_evidence["id"],
        },
        {
            "operator": "fix_flow_nucleus",
            "src": nucleus_map["id"],
            "tgt": iteration_evidence["id"],
        },
    ]
    return RealizerOutput(
        nodes=[new_phase_space, iteration_evidence, commutation_evidence],
        edges=edges,
        bindings={
            "phase_space": new_phase_space["id"],
            "fix_flow_nucleus_iteration_evidence": iteration_evidence["id"],
            "commutation_evidence": commutation_evidence["id"],
        },
    )
