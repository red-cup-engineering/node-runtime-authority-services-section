"""Finite nucleus law checker realizer."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def _leq(order: dict, a: str, b: str) -> bool:
    return a == b or b in order.get(a, [])


def _check_nucleus(profile: dict) -> (List[str], List[dict]):
    elems = profile.get("elements", [])
    nu = profile.get("nucleus_map", {}) or {}
    issues: List[str] = []
    checks: List[dict] = []
    order = profile.get("order", {})
    meet = profile.get("meet", {}) or {}

    if not nu:
        issues.append("Missing nucleus_map")
        checks.append({"law": "total", "status": "fail", "counterexample": None})

    # Totality, closure, extensive, idempotent
    for a in elems:
        na = nu.get(a)
        if na is None:
            issues.append(f"Missing nucleus_map entry for {a}")
            checks.append({"law": "total", "status": "fail", "counterexample": {"a": a}})
            continue
        if na not in elems:
            issues.append(f"Nucleus target {na} not in elements for {a}")
            checks.append({"law": "closure", "status": "fail", "counterexample": {"a": a, "nu_a": na}})
        if not _leq(order, a, na):
            issues.append(f"Extensive fail: {a} !<= ν(a)={na}")
            checks.append({"law": "extensive", "status": "fail", "counterexample": {"a": a, "nu_a": na}})
        nna = nu.get(na)
        if nna is not None and nna != na:
            issues.append(f"Idempotent fail: ν(ν({a}))={nna} != {na}")
            checks.append({"law": "idempotent", "status": "fail", "counterexample": {"a": a, "nu_a": na, "nu_nu_a": nna}})

    # Monotone: a<=b -> ν(a)<=ν(b)
    for a in elems:
        for b in elems:
            if not _leq(order, a, b):
                continue
            na = nu.get(a)
            nb = nu.get(b)
            if na is None or nb is None:
                continue
            if not _leq(order, na, nb):
                issues.append(f"Monotonicity fail: {a}<={b} but ν(a)!<=ν(b)")
                checks.append({"law": "monotone", "status": "fail", "counterexample": {"a": a, "b": b, "nu_a": na, "nu_b": nb}})

    # Absorb / Equalize: ν(a ∧ ν(b)) = ν(a ∧ b)
    if meet:
        for a in elems:
            for b in elems:
                ab = meet.get(a, {}).get(b)
                anb = meet.get(a, {}).get(nu.get(b, b))
                if ab is None or anb is None:
                    continue
                left = nu.get(anb, anb)
                right = nu.get(ab, ab)
                if left != right:
                    issues.append(f"Absorb fail: ν({a}∧ν({b}))={left} != ν({a}∧{b})={right}")
                    checks.append({"law": "absorb", "status": "fail", "counterexample": {"a": a, "b": b, "left": left, "right": right}})
                    checks.append({"law": "equalize", "status": "fail", "counterexample": {"a": a, "b": b, "left": left, "right": right}})

    # Fixed-point closure: ν(x)=x should be fixed under ν
    for a in elems:
        na = nu.get(a)
        if na == a and nu.get(na) != na:
            issues.append(f"Fixed-point closure fail: ν({a})={a} but ν(ν({a}))={nu.get(na)}")
            checks.append({"law": "fixed_point", "status": "fail", "counterexample": {"a": a, "nu_a": na, "nu_nu_a": nu.get(na)}})

    if not issues:
        checks.append({"law": "nucleus_laws", "status": "pass", "counterexample": None})
    # Fixed points (explicit)
    fixed_set = [a for a in elems if nu.get(a) == a]
    return issues, checks, fixed_set


def nucleus_laws(graph, payloads: List[dict], ctx=None):
    """Emit a nucleus_laws_evidence carrier with status."""
    if len(payloads) != 1 or payloads[0].get("kind") != "profile":
        raise LoaderError("nucleus_laws expects a single profile payload")
    profile = payloads[0]
    issues, checks, fixed_set = _check_nucleus(profile)
    status = "pass" if not issues else "fail"
    evidence = assign_canonical_id(
        {
            "kind": "nucleus_laws_evidence",
            "profile_id": profile["id"],
            "status": status,
            "issues": issues,
            "checks": checks,
            "nucleus_fixed": fixed_set,
        }
    )
    if status == "fail":
        raise LoaderError(f"Nucleus law check failed: {issues[0]}")
    return [evidence]
