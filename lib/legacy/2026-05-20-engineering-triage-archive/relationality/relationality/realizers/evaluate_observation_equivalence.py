from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    evaluate_observation_equivalence realizer.

    Input
    -----
    observation_equivalence:
        ObservationEquivalence carrier encoding an equivalence relation on a
        finite set of observations.

    Semantics
    ---------
    Validate the carrier shape (delegated to the validation layer) and emit
    an observation_equivalence_evidence node recording basic evaluation
    witnesses:

    - evaluation_witnesses summarize the number of observations and classes.
    - normalization_witnesses record that no additional normalization has
      been applied at this stage (iterations == 0).
    """
    eq = inputs.get("observation_equivalence")
    if eq is None:
        raise KeyError("evaluate_observation_equivalence requires 'observation_equivalence' input")
    if eq.get("kind") != "observation_equivalence":
        raise LawValidationError(
            "evaluate_observation_equivalence input must have kind 'observation_equivalence'"
        )

    obs_ids = eq.get("observation_ids", [])
    classes = eq.get("equivalence_classes") or []
    class_count = len(classes) if classes else 0

    evidence = {
        "kind": "observation_equivalence_evidence",
        "equivalence_id": eq["id"],
        "evaluation_witnesses": {
            "observation_count": len(obs_ids),
            "class_count": class_count,
        },
        "normalization_witnesses": {
            "iterations": 0,
        },
        "status": "pass",
        "act_ref": "EvaluateObservationEquivalence",
    }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "evaluate_observation_equivalence",
        "src": eq["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"observation_equivalence_evidence": evidence["id"]},
    )

