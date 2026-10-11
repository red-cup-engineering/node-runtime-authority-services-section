from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _find_observation_equivalence(graph, element: str) -> dict | None:
    candidates: List[dict] = []
    for node in getattr(graph, "nodes", {}).values():
        if node.get("kind") != "observation_equivalence":
            continue
        ids = node.get("observation_ids", [])
        if element in ids:
            candidates.append(node)
    if not candidates:
        return None
    if len(candidates) > 1:
        raise LawValidationError(
            "stabilized_observation_check found multiple observation_equivalence carriers "
            "containing the observation element"
        )
    return candidates[0]


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    stabilized_observation_check realizer.

    Input
    -----
    observation:
        Stabilized Observation carrier (kind ``observation``).

    Semantics
    ---------
    Verifies stabilization closure by checking that the observation's element
    is the canonical representative of its equivalence class with respect to
    an observation_equivalence carrier in the graph. Emits a
    stabilized_observation_evidence node recording witnesses and status.
    """
    observation = inputs.get("observation")
    if observation is None:
        raise KeyError("stabilized_observation_check requires 'observation' input")
    if observation.get("kind") != "observation":
        raise LawValidationError("stabilized_observation_check input must have kind 'observation'")

    element = observation.get("element")
    if not isinstance(element, str):
        raise LawValidationError("stabilized_observation_check requires observation.element to be a string")

    eq = _find_observation_equivalence(graph, element)
    if eq is None:
        status = "fail"
        witnesses = {}
        counterexample = {
            "reason": "no observation_equivalence carrier found for observation element",
            "element": element,
        }
    else:
        table = eq.get("equivalence_table", {})
        representative = table.get(element)
        witnesses = {
            "equivalence_id": eq["id"],
            "representative": representative,
        }
        if representative is None:
            status = "fail"
            counterexample = {
                "reason": "equivalence_table missing entry for observation.element",
                "element": element,
            }
        elif representative != element:
            status = "fail"
            counterexample = {
                "reason": "observation.element is not the canonical representative",
                "element": element,
                "representative": representative,
            }
        else:
            status = "pass"
            counterexample = None

    evidence = {
        "kind": "stabilized_observation_evidence",
        "observation_id": observation["id"],
        "equivalence_witnesses": witnesses,
        "status": status,
        "act_ref": "StabilizedObservationCheck",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "stabilized_observation_check",
        "src": observation["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"stabilized_observation_evidence": evidence["id"]},
    )
