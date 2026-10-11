"""Check shuffle equivalence of a trace (toy version)."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def _check_shuffle(trace: dict) -> (List[str], List[dict]):
    issues = []
    checks = []
    head = trace.get("head", [])
    tail = trace.get("tail", [])
    if not isinstance(head, list) or not isinstance(tail, list):
        issues.append("Head/tail not lists")
        checks.append({"law": "structure", "status": "fail", "counterexample": None})
    else:
        # For this toy check, ensure no duplicates between head and tail.
        overlap = set(head) & set(tail)
        if overlap:
            issues.append("Head/tail overlap")
            checks.append({"law": "disjoint", "status": "fail", "counterexample": {"overlap": list(overlap)}})
    if not checks:
        checks.append({"law": "shuffle_equivalence", "status": "pass", "counterexample": None})
    return issues, checks


def shuffle_equivalence(graph, payloads: List[dict], ctx=None):
    if len(payloads) != 1 or payloads[0].get("kind") != "trace":
        raise LoaderError("shuffle_equivalence expects a single trace")
    trace = payloads[0]
    issues, checks = _check_shuffle(trace)
    status = "pass" if not issues else "fail"
    evidence = assign_canonical_id(
        {"kind": "shuffle_equivalence_evidence", "status": status, "issues": issues, "checks": checks}
    )
    if status == "fail":
        raise LoaderError(f"Shuffle equivalence failed: {issues[0]}")
    return [evidence]
