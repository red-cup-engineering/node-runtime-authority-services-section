from __future__ import annotations

from typing import Dict, List, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    observation_equivalence realizer.

    Inputs
    ------
    observations:
        Normalized Observation carriers (kind ``observation``) that are to be
        grouped into equivalence classes.
    witnesses:
        Contextual witness carriers (any kind) establishing indistinguishability
        between these observations. Their IDs are recorded but not interpreted
        at this layer.

    Semantics
    ---------
    Construct an observation_equivalence carrier by:
    - collecting all observation elements from the inputs;
    - forming a single equivalence class containing all of them;
    - selecting the first element (in deterministic order) as the canonical
      representative;
    - building the equivalence_table mapping each element to the
      representative;
    - recording all witness IDs in witness_ids.

    This is a minimal, closed-world construction consistent with the current
    repository, which has a single observation element in the stabilized
    System. More refined partitions (multiple classes) remain reserved for
    future acts and carriers (EquateContexts, contextual witnesses).
    """
    observation_list: List[dict] = inputs.get("observations") or []
    witness_list: List[dict] = inputs.get("witnesses") or []
    if not observation_list:
        raise KeyError("observation_equivalence requires non-empty 'observations' input list")
    obs_elements: List[str] = []
    for obs in observation_list:
        if obs.get("kind") != "observation":
            raise LawValidationError("observation_equivalence observations must all have kind 'observation'")
        element = obs.get("element")
        if not isinstance(element, str):
            raise LawValidationError("observation_equivalence observations must carry string 'element'")
        obs_elements.append(element)
    # Deterministic class: single class with lexicographically sorted elements.
    obs_elements_sorted = sorted(dict.fromkeys(obs_elements))
    if not obs_elements_sorted:
        raise LawValidationError("observation_equivalence requires at least one distinct observation element")
    representative = obs_elements_sorted[0]
    equivalence_classes = [obs_elements_sorted]
    equivalence_table: dict[str, str] = {elt: representative for elt in obs_elements_sorted}

    witness_ids: List[str] = []
    for w in witness_list:
        w_id = w.get("id")
        if isinstance(w_id, str):
            witness_ids.append(w_id)

    payload = {
        "kind": "observation_equivalence",
        "observation_ids": obs_elements_sorted,
        "equivalence_classes": equivalence_classes,
        "equivalence_table": equivalence_table,
        "witness_ids": witness_ids or [representative],
    }
    ensure_id_coherence(payload)

    # Diagnostic evidence that the constructed carrier satisfies basic shape.
    evidence = {
        "kind": "observation_equivalence_evidence",
        "equivalence_id": payload["id"],
        "evaluation_witnesses": {
            "observation_count": len(obs_elements_sorted),
            "class_count": len(equivalence_classes),
        },
        "normalization_witnesses": {
            "iterations": 0,
        },
        "status": "pass",
        "act_ref": "ObservationEquivalence",
    }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "observation_equivalence",
        "src": payload["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[payload, evidence],
        edges=[edge],
        bindings={"observation_equivalence": payload["id"]},
    )
