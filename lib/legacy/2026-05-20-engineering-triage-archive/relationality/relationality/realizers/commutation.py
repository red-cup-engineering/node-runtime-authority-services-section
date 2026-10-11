"""Flow–nucleus commutation checker."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def _check_commutation(profile: dict) -> List[str]:
    elems = profile.get("elements", [])
    flow = profile.get("flow_map", {})
    nu = profile.get("nucleus_map", {})
    issues = []
    checks = []
    if not flow or not nu:
        issues.append("Missing flow_map or nucleus_map")
        checks.append({"law": "total", "status": "fail", "counterexample": None})
        return issues, checks
    for a in elems:
        Fa = flow.get(a)
        na = nu.get(a)
        if Fa is None or na is None:
            msg = f"Missing flow/nucleus for {a}"
            issues.append(msg)
            checks.append({"law": "total", "status": "fail", "counterexample": {"a": a}})
            continue
        nFa = nu.get(Fa)
        Fna = flow.get(na)
        if nFa is None or Fna is None:
            msg = f"Missing composite for {a}"
            issues.append(msg)
            checks.append({"law": "total", "status": "fail", "counterexample": {"a": a}})
            continue
        if nFa != Fna:
            msg = f"Commutation fail: ν(F({a}))={nFa} != F(ν({a}))={Fna}"
            issues.append(msg)
            checks.append({"law": "commutation", "status": "fail", "counterexample": {"a": a, "nFa": nFa, "Fna": Fna}})
    if not issues:
        checks.append({"law": "commutation", "status": "pass", "counterexample": None})
    return issues, checks


def commutation(graph, payloads: List[dict], ctx=None):
    """Emit a commutation_evidence carrier with status."""
    if len(payloads) != 1 or payloads[0].get("kind") != "profile":
        raise LoaderError("commutation expects a single profile payload")
    profile = payloads[0]
    issues, checks = _check_commutation(profile)
    status = "pass" if not issues else "fail"
    evidence = assign_canonical_id(
        {
            "kind": "commutation_evidence",
            "profile_id": profile["id"],
            "status": status,
            "issues": issues,
            "checks": checks,
        }
    )
    if status == "fail":
        raise LoaderError(f"Commutation check failed: {issues[0]}")
    return [evidence]
