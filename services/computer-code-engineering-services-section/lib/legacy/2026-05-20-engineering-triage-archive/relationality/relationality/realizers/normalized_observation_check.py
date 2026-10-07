from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.realizers.normalize_observation import realize as normalize_observation
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    normalized_observation_check realizer.

    Input
    -----
    observation:
        Observation carrier expected to be normalized.

    Semantics
    ---------
    Re-runs NormalizeObservation on the supplied observation to confirm
    fixed-point behavior and emits normalized_observation_evidence:

    - status == 'pass' when the observation is already normalized;
    - status == 'fail' with counterexample when one additional normalization
      step changes the element.
    """
    observation = inputs.get("observation")
    if observation is None:
        raise KeyError("normalized_observation_check requires 'observation' input")
    if observation.get("kind") != "observation":
        raise LawValidationError("normalized_observation_check input must have kind 'observation'")

    original_id = observation["id"]
    original_element = observation.get("element")
    if not isinstance(original_element, str):
        raise LawValidationError("normalized_observation_check requires observation.element to be a string")

    # Run a single normalization step using the existing NormalizeObservation
    # realizer in an ephemeral graph context.
    temp_graph = graph
    output = normalize_observation(
        temp_graph,
        {"observation": observation},
        {"runbook": {"id": "0" * 64}, "step": {"step_index": 0}},
    )
    normalized = output.nodes[0]
    new_element = normalized.get("element")

    changed = new_element != original_element
    status = "fail" if changed else "pass"
    evidence = {
        "kind": "normalized_observation_evidence",
        "observation_id": original_id,
        "iteration_count": 1,
        "status": status,
        "act_ref": "NormalizedObservationCheck",
    }
    if changed:
        evidence["counterexample"] = {
            "reason": "single NormalizeObservation step changed observation.element",
            "before": original_element,
            "after": new_element,
        }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "normalized_observation_check",
        "src": original_id,
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"normalized_observation_evidence": evidence["id"]},
    )

