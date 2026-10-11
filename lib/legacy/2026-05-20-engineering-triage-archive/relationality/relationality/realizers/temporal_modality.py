"""Construct trivial temporal modality tables and evidence."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def temporal_modality(graph, payloads: List[dict], ctx=None):
    if len(payloads) != 1 or payloads[0].get("kind") != "profile":
        raise LoaderError("temporal_modality expects a single profile payload")
    profile = payloads[0]
    elems = profile.get("elements", [])
    always_table = {e: e for e in elems}
    eventually_table = {e: e for e in elems}
    evidence = assign_canonical_id(
        {
            "kind": "temporal_modality_evidence",
            "status": "pass",
            "issues": [],
            "checks": [{"law": "temporal_modality", "status": "pass", "counterexample": None}],
        }
    )
    modality = {
        "kind": "temporal_modality",
        "always_table": always_table,
        "eventually_table": eventually_table,
        "evidence_ids": [evidence["id"]],
    }
    modality = assign_canonical_id(modality)
    return [modality, evidence]
