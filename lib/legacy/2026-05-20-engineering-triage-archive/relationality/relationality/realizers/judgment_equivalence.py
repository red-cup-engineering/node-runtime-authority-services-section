from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_judgment_equivalence


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    judgment_equivalence realizer.

    Inputs
    ------
    judgments:
        Normalized Judgment carriers (kind ``judgment``) that are to be
        grouped into an indistinguishability class.
    witnesses:
        Witness carriers (typically judgment-triad witnesses) establishing
        indistinguishability between these judgments. Their IDs are recorded
        but not interpreted at this layer.

    Semantics
    ---------
    Construct a judgment_equivalence carrier by:
    - collecting all judgment IDs from the inputs;
    - forming a single equivalence class containing all of them;
    - recording all witness IDs in witness_ids;
    - enforcing structural equivalence laws via validation.

    This is a minimal, closed-world construction consistent with the current
    repository. More refined partitions (multiple classes) and richer witness
    structure are reserved for future acts and carriers.
    """
    judgment_list: List[dict] = inputs.get("judgments") or []
    witness_list: List[dict] = inputs.get("witnesses") or []
    if not judgment_list:
        raise KeyError("judgment_equivalence requires non-empty 'judgments' input list")

    judgment_ids: List[str] = []
    for j in judgment_list:
        if j.get("kind") != "judgment":
            raise LawValidationError("judgment_equivalence judgments must all have kind 'judgment'")
        j_id = j.get("id")
        if not isinstance(j_id, str):
            raise LawValidationError("judgment_equivalence judgments must carry string 'id'")
        judgment_ids.append(j_id)

    # Deterministic class: single class with lexicographically sorted IDs.
    judgment_ids_sorted = sorted(dict.fromkeys(judgment_ids))
    if not judgment_ids_sorted:
        raise LawValidationError("judgment_equivalence requires at least one distinct judgment ID")
    equivalence_classes = [judgment_ids_sorted]

    witness_ids: List[str] = []
    for w in witness_list:
        w_id = w.get("id")
        if isinstance(w_id, str):
            witness_ids.append(w_id)
    if not witness_ids:
        raise LawValidationError("judgment_equivalence requires at least one witness id")

    payload = {
        "kind": "judgment_equivalence",
        "judgment_ids": judgment_ids_sorted,
        "equivalence_classes": equivalence_classes,
        "witness_ids": witness_ids,
    }
    # Enforce structural laws on the carrier before assigning its ID.
    validate_judgment_equivalence(payload)
    ensure_id_coherence(payload)

    evidence = {
        "kind": "judgment_equivalence_evidence",
        "judgment_equivalence_id": payload["id"],
        "witness_ids": list(witness_ids),
        "status": "pass",
        "act_ref": "JudgmentEquivalence",
    }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "judgment_equivalence",
        "src": payload["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[payload, evidence],
        edges=[edge],
        bindings={"judgment_equivalence": payload["id"]},
    )

