from __future__ import annotations

from typing import Dict, Iterable, Mapping, Set, Tuple

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _pairs_from_classes(classes: Iterable[Iterable[str]]) -> Set[Tuple[str, str]]:
    pairs: Set[Tuple[str, str]] = set()
    for cls in classes:
        cls_list = list(cls)
        for i, a in enumerate(cls_list):
            for b in cls_list[i:]:
                pairs.add((a, b))
                pairs.add((b, a))
    return pairs


def _pairs_from_relation_table(table: Iterable[Iterable[str]]) -> Set[Tuple[str, str]]:
    pairs: Set[Tuple[str, str]] = set()
    for entry in table:
        entry_list = list(entry)
        if len(entry_list) != 2:
            raise LawValidationError("judgment_equivalence relation_table entries must be [a, b]")
        a, b = entry_list
        pairs.add((a, b))
    return pairs


def _relation_from_payload(eq: Mapping[str, object]) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    ids = set(eq.get("judgment_ids") or [])
    classes = eq.get("equivalence_classes") or []
    table = eq.get("relation_table") or []
    if not ids:
        raise LawValidationError("judgment_equivalence must list non-empty judgment_ids")
    relation: Set[Tuple[str, str]] = set()
    if classes:
        relation |= _pairs_from_classes(classes)
    if table:
        relation |= _pairs_from_relation_table(table)
    # Ensure all endpoints lie in the declared set of ids.
    for a, b in relation:
        if a not in ids or b not in ids:
            raise LawValidationError("judgment_equivalence relation references id not in judgment_ids")
    return ids, relation


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    judgment_equivalence_check realizer.

    Input
    -----
    judgment_equivalence:
        JudgmentEquivalence carrier encoding a relation on judgments.

    Semantics
    ---------
    Diagnostic check that the encoded relation is an equivalence relation
    on the declared ``judgment_ids``:
    - reflexive: (x, x) in R for every x;
    - symmetric: (x, y) in R implies (y, x) in R;
    - transitive: (x, y) and (y, z) in R implies (x, z) in R.

    It also ensures that witness_ids is non-empty. The check does not
    interpret the witnesses or the underlying judgments; it verifies only
    the relational structure mandated by the acts.
    """
    eq = inputs.get("judgment_equivalence")
    if eq is None:
        raise KeyError("judgment_equivalence_check requires 'judgment_equivalence' input")
    if eq.get("kind") != "judgment_equivalence":
        raise LawValidationError("judgment_equivalence_check input must have kind 'judgment_equivalence'")

    ids, relation = _relation_from_payload(eq)
    witness_ids = eq.get("witness_ids") or []
    if not witness_ids:
        raise LawValidationError("judgment_equivalence must provide non-empty witness_ids")

    status = "pass"
    counterexample = None

    # Reflexivity.
    for x in ids:
        if (x, x) not in relation:
            status = "fail"
            counterexample = {"law": "reflexive", "x": x}
            break

    # Symmetry.
    if status == "pass":
        for a, b in relation:
            if (b, a) not in relation:
                status = "fail"
                counterexample = {"law": "symmetric", "a": a, "b": b}
                break

    # Transitivity.
    if status == "pass":
        for x in ids:
            for y in ids:
                if (x, y) not in relation:
                    continue
                for z in ids:
                    if (y, z) in relation and (x, z) not in relation:
                        status = "fail"
                        counterexample = {"law": "transitive", "x": x, "y": y, "z": z}
                        break
                if status == "fail":
                    break
            if status == "fail":
                break

    evidence: Dict[str, object] = {
        "kind": "judgment_equivalence_evidence",
        "judgment_equivalence_id": eq["id"],
        "witness_ids": list(witness_ids),
        "status": status,
        "act_ref": "JudgmentEquivalenceCheck",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "judgment_equivalence_check",
        "src": eq["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"judgment_equivalence_evidence": evidence["id"]},
    )

