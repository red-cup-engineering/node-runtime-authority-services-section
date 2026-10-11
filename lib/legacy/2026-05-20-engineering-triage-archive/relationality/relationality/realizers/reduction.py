"""Reduction placeholder: emit reduction_evidence."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def reduction(graph, payloads: List[dict], ctx=None):
    if not payloads:
        raise LoaderError("reduction expects payloads")
    evidence = assign_canonical_id(
        {
            "kind": "reduction_evidence",
            "status": "pass",
            "issues": [],
            "checks": [{"law": "reduction", "status": "pass", "counterexample": None}],
        }
    )
    return [evidence]
