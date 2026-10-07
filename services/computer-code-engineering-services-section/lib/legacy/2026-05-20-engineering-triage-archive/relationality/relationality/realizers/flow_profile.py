from __future__ import annotations

import copy
from typing import Dict, List, Optional

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    flow_profile realizer.

    Inputs
    ------
    phase_space:
        PhaseSpace carrier whose current_state is evolved by the flow.
    flow_map:
        FlowMap carrier encoding F:R→R over a finite lattice whose
        elements contain the phase_space states.

    Semantics
    ---------
    - Enforce flow laws (monotone, inflationary, distributive) on the
      finite carrier lattice referenced by flow_map.carrier_id.
    - Require that the phase_space.states embed into the flow_map
      carrier elements.
    - Update phase_space.current_state := F(current_state).
    - Canonicalize the updated phase_space and emit a flow_profile edge.
    """
    phase_space = inputs.get("phase_space")
    flow_map = inputs.get("flow_map")
    trace = inputs.get("trace")
    if phase_space is None or flow_map is None:
        raise KeyError("flow_profile requires 'phase_space' and 'flow_map' inputs")

    if phase_space.get("kind") != "phase_space":
        raise LawValidationError("flow_profile phase_space input must have kind 'phase_space'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("flow_profile flow_map input must have kind 'flow_map'")

    states = set(phase_space.get("states", []))
    flow_elements = set(flow_map.get("elements", []))
    if not states:
        raise LawValidationError("phase_space must declare at least one state")
    if not states.issubset(flow_elements):
        raise LawValidationError("phase_space states must be contained in flow_map elements")

    flow_table = flow_map["flow_table"]
    for state in states:
        if state not in flow_table:
            raise LawValidationError(f"flow_table missing entry for state {state}")
        if flow_table[state] not in flow_elements:
            raise LawValidationError(f"flow_table maps {state} outside carrier")

    current = phase_space.get("current_state")
    if current not in states:
        raise LawValidationError("current_state must be one of the phase_space states")

    new_state = flow_table[current]

    new_phase_space = copy.deepcopy(phase_space)
    new_phase_space["current_state"] = new_state
    # Recompute ID canonically for the updated carrier.
    new_phase_space.pop("id", None)
    ensure_id_coherence(new_phase_space)
    nodes = [new_phase_space]
    edges = [
        {
            "operator": "flow_profile",
            "src": phase_space["id"],
            "tgt": new_phase_space["id"],
        },
        {
            "operator": "flow_profile",
            "src": flow_map["id"],
            "tgt": new_phase_space["id"],
        },
    ]
    bindings: Dict[str, str] = {"phase_space": new_phase_space["id"]}

    # Optional trace update: if a trace carrier is supplied, append the new
    # state as the next head element, respecting the head/tail recursion and
    # initializing or lifting shuffle metadata in the same style as the trace
    # realizers.
    if trace is not None:
        if trace.get("kind") != "trace":
            raise LawValidationError("flow_profile trace input must have kind 'trace'")
        # Validate basic trace invariants.
        validate_trace(trace)
        old_elements: List[str] = list(trace["elements"])
        new_elements: List[str] = [new_state] + old_elements
        new_trace: dict = {
            "kind": "trace",
            "elements": new_elements,
            "head": new_state,
            "tail": new_elements[1:],
        }
        shuffle = trace.get("shuffle_metadata")
        if shuffle is not None:
            perms = shuffle.get("permutations", [])
            lifted_perms: List[List[int]] = []
            length_old = len(old_elements)
            for perm in perms:
                if sorted(perm) != list(range(length_old)):
                    raise LawValidationError("flow_profile input trace has invalid shuffle permutation")
                lifted_perms.append([0] + [idx + 1 for idx in perm])
            new_shuffle: dict = {"permutations": lifted_perms}
            canonical_rep = shuffle.get("canonical_rep")
            if canonical_rep is not None and canonical_rep not in old_elements:
                raise LawValidationError("flow_profile input trace has invalid canonical_rep")
            # Canonical representative is left unchanged; CollapseShuffle
            # continues to act via shuffle_trace when desired.
            if canonical_rep is not None:
                new_shuffle["canonical_rep"] = canonical_rep
            new_trace["shuffle_metadata"] = new_shuffle
        else:
            new_trace["shuffle_metadata"] = {
                "permutations": [list(range(len(new_elements)))],
                "canonical_rep": new_state,
            }
        ensure_id_coherence(new_trace)
        nodes.append(new_trace)
        edges.append(
            {
                "operator": "flow_profile",
                "src": trace["id"],
                "tgt": new_trace["id"],
            }
        )
        bindings["trace"] = new_trace["id"]

    return RealizerOutput(
        nodes=nodes,
        edges=edges,
        bindings=bindings,
    )
