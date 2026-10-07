from __future__ import annotations

from typing import Dict, List, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_evaluation_equivalence


def _canonical_classes(classes: List[List[str]] | None) -> List[List[str]] | None:
    if not classes:
        return None
    canonical: List[List[str]] = []
    for cls in classes:
        canonical.append(sorted(cls))
    canonical.sort(key=lambda c: c[0])
    return canonical


def _canonical_relation(table: List[List[str]] | None) -> List[List[str]] | None:
    if not table:
        return None
    # Preserve given ordering; validation has already enforced structural laws.
    return [list(pair) for pair in table]


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    evaluation_equivalence realizer.

    Input
    -----
    evaluation_equivalence:
        Carrier encoding an equivalence relation on evaluated carriers
        (evaluated_observation / evaluated_judgment) together with
        witness_ids.

    Semantics
    ---------
    - Revalidate the carrier against schema and equivalence laws.
    - Emit an evaluation_equivalence_evidence node that:
        * records the input_ids;
        * records equivalence_classes and relation_table (when present),
          with deterministic ordering;
        * mirrors witness_ids; and
        * sets widened_ids equal to input_ids in this initial fragment.
    """
    eq = inputs.get("evaluation_equivalence")
    if eq is None:
        raise KeyError("evaluation_equivalence realizer requires 'evaluation_equivalence' input")
    if eq.get("kind") != "evaluation_equivalence":
        raise LawValidationError("evaluation_equivalence input must have kind 'evaluation_equivalence'")

    # Structural and law validation of the carrier.
    validate_evaluation_equivalence(eq)

    input_ids: List[str] = list(eq.get("input_ids", []))
    classes = _canonical_classes(eq.get("equivalence_classes"))
    relation_table = _canonical_relation(eq.get("relation_table"))
    witness_ids: List[str] = list(eq.get("witness_ids", []))

    evidence: Mapping[str, object] = {
        "kind": "evaluation_equivalence_evidence",
        "input_ids": input_ids,
        "equivalence_classes": classes or [],
        "relation_table": relation_table or [],
        "widened_ids": list(input_ids),
        "witness_ids": witness_ids,
        "status": "pass",
        "act_ref": "EvaluationEquivalence",
    }
    evidence = dict(evidence)
    ensure_id_coherence(evidence)

    edge = {
        "operator": "evaluation_equivalence",
        "src": eq["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"evaluation_equivalence_evidence": evidence["id"]},
    )

