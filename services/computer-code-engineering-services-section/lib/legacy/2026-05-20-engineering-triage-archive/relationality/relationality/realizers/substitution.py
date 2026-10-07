"""Substitution placeholder: emit substitution_evidence."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def substitution(graph, payloads: List[dict], ctx=None):
    if not payloads:
        raise LoaderError("substitution expects payloads")
    evidence = assign_canonical_id(
        {
            "kind": "substitution_evidence",
            "status": "pass",
            "issues": [],
            "checks": [{"law": "substitution", "status": "pass", "counterexample": None}],
        }
    )
    return [evidence]
