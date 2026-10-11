"""Discipline operator: link trace and judgment evidence into a fixed invariant."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def discipline_profile(graph, payloads: List[dict], ctx=None):
    """Combine profile, trace_evidence, and judgment_equivalence_evidence into fixed_invariants."""
    if not payloads:
        raise LoaderError("discipline_profile expects payloads")
    profile = next((p for p in payloads if p.get("kind") == "profile"), None)
    trace_ev = next((p for p in payloads if p.get("kind") == "trace_evidence"), None)
    judgment_ev = next((p for p in payloads if p.get("kind") == "judgment_equivalence_evidence"), None)
    if profile is None or trace_ev is None or judgment_ev is None:
        raise LoaderError("discipline_profile requires profile, trace_evidence, and judgment_equivalence_evidence")
    evidence_ids = []
    for ev in (trace_ev, judgment_ev):
        if ev:
            evidence_ids.append(ev["id"])

    inv = assign_canonical_id(
        {
            "kind": "fixed_invariants",
            "invariants": [profile["id"], trace_ev["id"], judgment_ev["id"]],
            "evidence_ids": evidence_ids,
            "geometry_tags": [],
        }
    )
    return [inv]
