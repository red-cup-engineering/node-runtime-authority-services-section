from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    evaluate_observation realizer.

    Inputs
    ------
    observation:
        Observation carrier (kind ``observation``) to be evaluated.

    Semantics
    ---------
    Realizes the EvaluateObservation act in the minimal fragment by
    packaging an evaluated_observation carrier that:
    - references the input observation by ID; and
    - records an evaluation witness ID equal to the observation ID,
      reflecting total, idempotent evaluation on this fragment.
    """
    observation = inputs.get("observation")
    if observation is None:
        raise KeyError("evaluate_observation requires 'observation' input")
    if observation.get("kind") != "observation":
        raise LawValidationError("evaluate_observation input must have kind 'observation'")

    evaluated = {
        "kind": "evaluated_observation",
        "observation_id": observation["id"],
        "evaluation_witness_id": observation["id"],
        "act_ref": "EvaluateObservation",
    }
    ensure_id_coherence(evaluated)

    edge = {
        "operator": "evaluate_observation",
        "src": observation["id"],
        "tgt": evaluated["id"],
    }

    return RealizerOutput(
        nodes=[evaluated],
        edges=[edge],
        bindings={"evaluated_observation": evaluated["id"]},
    )

