"""Trace law checks: head/tail recursion."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def _check_trace(trace: dict) -> (List[str], List[dict]):
    issues = []
    checks = []
    head = trace.get("head", [])
    tail = trace.get("tail", [])
    if head is None or tail is None:
        issues.append("Missing head or tail")
        checks.append({"law": "total", "status": "fail", "counterexample": None})
    # Recursion: head must be non-empty unless tail empty
    if not isinstance(head, list) or not isinstance(tail, list):
        issues.append("Head or tail not list")
        checks.append({"law": "structure", "status": "fail", "counterexample": None})
    else:
        if len(head) == 0 and len(tail) > 0:
            issues.append("Empty head with non-empty tail")
            checks.append({"law": "recursion", "status": "fail", "counterexample": {"head": head, "tail": tail}})
        if any(not isinstance(x, str) for x in head + tail):
            issues.append("Head/tail elements must be strings")
            checks.append({"law": "structure", "status": "fail", "counterexample": {"head": head, "tail": tail}})
        # Recursion: a trace is determined by head[0] and tail
        if head and tail and head[0] in tail:
            issues.append("Head element appears in tail; ill-founded recursion")
            checks.append({"law": "recursion", "status": "fail", "counterexample": {"head": head, "tail": tail}})
    if not checks:
        checks.append({"law": "trace_laws", "status": "pass", "counterexample": None})
    return issues, checks


def trace_laws(graph, payloads: List[dict], ctx=None):
    """Emit trace_evidence with status."""
    if len(payloads) != 1 or payloads[0].get("kind") != "trace":
        raise LoaderError("trace_laws expects a single trace payload")
    trace = payloads[0]
    issues, checks = _check_trace(trace)
    status = "pass" if not issues else "fail"
    evidence = assign_canonical_id(
        {
            "kind": "trace_evidence",
            "trace_id": trace["id"],
            "status": status,
            "issues": issues,
            "checks": checks,
            "kernel_pairs": trace.get("kernel_pairs", {}),
        }
    )
    if status == "fail":
        raise LoaderError(f"Trace law check failed: {issues[0]}")
    return [evidence]
