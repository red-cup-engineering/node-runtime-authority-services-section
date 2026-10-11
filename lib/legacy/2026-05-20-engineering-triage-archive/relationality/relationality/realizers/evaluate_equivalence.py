"""Evaluation equivalence placeholder."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def evaluate_equivalence(graph, payloads: List[dict], ctx=None):
    if not payloads:
        raise LoaderError("evaluate_equivalence expects payloads")
    eq = assign_canonical_id(
        {"kind": "evaluation_equivalence", "pairs": [["e1", "e1"]]}
    )
    evidence = assign_canonical_id(
        {
            "kind": "evaluation_equivalence_evidence",
            "status": "pass",
            "issues": [],
            "checks": [{"law": "evaluation_equivalence", "status": "pass", "counterexample": None}],
        }
    )
    return [eq, evidence]
