from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _sorted_unique(seq: List[str]) -> List[str]:
    return sorted(dict.fromkeys(seq))


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    equate_judgment_observation realizer.

    Inputs
    ------
    observation_equivalence:
        ObservationEquivalence carrier whose observation_ids are the observed
        recognitions to be aligned with judgments.
    judgment_equivalence:
        JudgmentEquivalence carrier over the judgments that interpret those
        observations.

    Semantics
    ---------
    EquateJudgmentObservation asserts that the observational indistinguishability
    captured by observation_equivalence is aligned with the indistinguishability
    of the corresponding judgments. In this minimal fragment, alignment is
    enforced by requiring that the set of observation_ids equals the set of
    judgment_ids; when they differ, the realizer rejects with a LawValidationError.

    Evidence:
    - equate_judgment_observation_evidence with status 'pass' and references
      to the two equivalence carriers when the sets match exactly.
    """
    obs_eq = inputs.get("observation_equivalence")
    judg_eq = inputs.get("judgment_equivalence")
    if obs_eq is None or judg_eq is None:
        raise KeyError("equate_judgment_observation requires 'observation_equivalence' and 'judgment_equivalence' inputs")
    if obs_eq.get("kind") != "observation_equivalence":
        raise LawValidationError("equate_judgment_observation observation_equivalence input must have kind 'observation_equivalence'")
    if judg_eq.get("kind") != "judgment_equivalence":
        raise LawValidationError("equate_judgment_observation judgment_equivalence input must have kind 'judgment_equivalence'")

    obs_ids = _sorted_unique(list(obs_eq.get("observation_ids", [])))
    judg_ids = _sorted_unique(list(judg_eq.get("judgment_ids", [])))

    aligned = False
    # First, require direct alignment when possible.
    if obs_ids == judg_ids:
        aligned = True
    else:
        # Attempt to align via observation nodes that carry judgment_id.
        graph_nodes = getattr(graph, "nodes", {})
        mapped_judgment_ids: List[str] = []
        for obs_element in obs_ids:
            for node in graph_nodes.values():
                if node.get("kind") == "observation" and node.get("element") == obs_element:
                    j_id = node.get("judgment_id")
                    if isinstance(j_id, str):
                        mapped_judgment_ids.append(j_id)
        mapped_judgment_ids = _sorted_unique(mapped_judgment_ids)
        if mapped_judgment_ids == judg_ids and mapped_judgment_ids:
            aligned = True

    if not aligned:
        raise LawValidationError(
            "equate_judgment_observation requires observation equivalence to align with judgment equivalence"
        )

    evidence = {
        "kind": "equate_judgment_observation_evidence",
        "observation_equivalence_id": obs_eq["id"],
        "judgment_equivalence_id": judg_eq["id"],
        "status": "pass",
        "act_ref": "EquateJudgmentObservation",
    }
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "equate_judgment_observation",
            "src": obs_eq["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "equate_judgment_observation",
            "src": judg_eq["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"equate_judgment_observation_evidence": evidence["id"]},
    )
