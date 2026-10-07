from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    observation_equivalence_check realizer.

    Input
    -----
    observation_equivalence:
        ObservationEquivalence carrier.

    Semantics
    ---------
    Diagnostic check for observation equivalence carriers. Assuming the
    carrier has already passed structural and law validation, emit an
    observation_equivalence_evidence node summarizing the relation.
    """
    eq = inputs.get("observation_equivalence")
    if eq is None:
        raise KeyError("observation_equivalence_check requires 'observation_equivalence' input")
    if eq.get("kind") != "observation_equivalence":
        raise LawValidationError(
            "observation_equivalence_check input must have kind 'observation_equivalence'"
        )

    obs_ids = eq.get("observation_ids", [])
    classes = eq.get("equivalence_classes") or []

    evidence = {
        "kind": "observation_equivalence_evidence",
        "equivalence_id": eq["id"],
        "evaluation_witnesses": {
            "observation_count": len(obs_ids),
            "class_count": len(classes),
        },
        "normalization_witnesses": {
            # The check realizer does not normalize; it only certifies the
            # relation as currently encoded.
            "iterations": 0,
        },
        "status": "pass",
        "act_ref": "ObservationEquivalenceCheck",
    }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "observation_equivalence_check",
        "src": eq["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"observation_equivalence_evidence": evidence["id"]},
    )

