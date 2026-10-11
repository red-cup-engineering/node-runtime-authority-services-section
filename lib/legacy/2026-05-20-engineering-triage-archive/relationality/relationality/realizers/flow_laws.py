"""Finite flow law checker realizer."""

from __future__ import annotations

from typing import List, Tuple

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def _leq(order: dict, a: str, b: str) -> bool:
    return a == b or b in order.get(a, [])


def _iterate_flow(flow: dict, start: str) -> Tuple[str, List[str]]:
    """Iterate flow_map from start until fixed or detect a cycle."""
    seen = []
    current = start
    while True:
        if current in seen:
            return current, seen + [current]
        seen.append(current)
        nxt = flow.get(current)
        if nxt is None:
            return current, seen
        if nxt == current:
            return current, seen
        current = nxt


def _check_flow(profile: dict) -> (List[str], List[dict]):
    elems = profile.get("elements", [])
    flow = profile.get("flow_map", {}) or {}
    issues = []
    checks = []
    order = profile.get("order", {})
    meet = profile.get("meet", {})

    if not flow:
        issues.append("Missing flow_map")
        checks.append({"law": "total", "status": "fail", "counterexample": None})

    # Monotonicity: if a<=b then F(a)<=F(b)
    for a in elems:
        Fa = flow.get(a)
        if Fa is None:
            msg = f"Missing flow_map entry for {a}"
            issues.append(msg)
            checks.append({"law": "total", "status": "fail", "counterexample": {"a": a}})
            continue
        if Fa not in elems:
            msg = f"Flow target {Fa} not in elements for {a}"
            issues.append(msg)
            checks.append({"law": "closure", "status": "fail", "counterexample": {"a": a, "Fa": Fa}})
        for b in order.get(a, []):
            Fb = flow.get(b)
            if Fb is None:
                msg = f"Missing flow_map entry for {b}"
                issues.append(msg)
                checks.append({"law": "total", "status": "fail", "counterexample": {"b": b}})
                continue
            if not _leq(order, Fa, Fb):
                msg = f"Monotonicity fail: {a}<={b} but F(a) !<= F(b)"
                issues.append(msg)
                checks.append(
                    {
                        "law": "monotone",
                        "status": "fail",
                        "counterexample": {"a": a, "b": b, "Fa": Fa, "Fb": Fb},
                    }
                )
    # Monotonicity across all pairs (not just cover relation)
    for a in elems:
        Fa = flow.get(a)
        if Fa is None:
            continue
        for b in elems:
            Fb = flow.get(b)
            if Fb is None:
                continue
            if _leq(order, a, b) and not _leq(order, Fa, Fb):
                msg = f"Monotonicity fail: {a}<={b} but F(a)!<=F(b)"
                issues.append(msg)
                checks.append({"law": "monotone", "status": "fail", "counterexample": {"a": a, "b": b, "Fa": Fa, "Fb": Fb}})
    # Inflationary: a <= F(a)
    for a in elems:
        Fa = flow.get(a)
        if Fa is None:
            continue
        if not _leq(order, a, Fa):
            msg = f"Inflationary fail: {a} not <= F(a)={Fa}"
            issues.append(msg)
            checks.append({"law": "inflationary", "status": "fail", "counterexample": {"a": a, "Fa": Fa}})
    # Distributive inequality: F(a∧b) <= F(a) ∧ F(b) and equalize F(a∧F(b)) <= F(a∧b)
    if meet:
        for a in elems:
            for b in elems:
                mab = meet.get(a, {}).get(b)
                if mab is None:
                    continue
                Fab = flow.get(mab)
                Fa = flow.get(a)
                Fb = flow.get(b)
                if Fab is None or Fa is None or Fb is None:
                    continue
                meet_Fa_Fb = meet.get(Fa, {}).get(Fb)
                if meet_Fa_Fb and not _leq(order, Fab, meet_Fa_Fb):
                    msg = f"Distributive fail: F({a}∧{b}) !<= F({a})∧F({b})"
                    issues.append(msg)
                    checks.append(
                        {
                            "law": "distribute_meet",
                            "status": "fail",
                            "counterexample": {"a": a, "b": b, "Fab": Fab, "Fa": Fa, "Fb": Fb},
                        }
                    )
                mab_flowb = meet.get(a, {}).get(Fb)
                if mab_flowb is not None and Fab is not None:
                    left = flow.get(mab_flowb)
                    right = Fab
                    if left is not None and not _leq(order, left, right):
                        msg = f"Equalize fail: F({a}∧F({b})) !<= F({a}∧{b})"
                        issues.append(msg)
                        checks.append(
                            {
                                "law": "equalize",
                                "status": "fail",
                                "counterexample": {"a": a, "b": b, "left": left, "right": right},
                            }
                        )
    if not checks and not issues:
        checks.append({"law": "flow_laws", "status": "pass", "counterexample": None})

    # Fixed-point convergence / aperiodicity
    for a in elems:
        fixed, path = _iterate_flow(flow, a)
        if len(path) > len(set(path)):
            issues.append(f"Cycle detected in flow iterates from {a}: {path}")
            checks.append({"law": "aperiodic", "status": "fail", "counterexample": {"path": path}})
            continue
        # fixed is last element in path (either cycle entry or fixed point)
        if flow.get(fixed) not in (fixed, None):
            issues.append(f"Non-fixed terminal iterate for {a}: F({fixed})={flow.get(fixed)}")
            checks.append({"law": "fixed_point", "status": "fail", "counterexample": {"a": a, "fixed": fixed}})
    if not issues and all(c.get("law") != "flow_laws" for c in checks):
        checks.append({"law": "flow_laws", "status": "pass", "counterexample": None})
    return issues, checks


def flow_laws(graph, payloads: List[dict], ctx=None):
    """Emit a flow_laws_evidence carrier with status."""
    if len(payloads) != 1 or payloads[0].get("kind") != "profile":
        raise LoaderError("flow_laws expects a single profile payload")
    profile = payloads[0]
    issues, checks = _check_flow(profile)
    status = "pass" if not issues else "fail"
    fixed_set = []
    # Fixed-point convergence / aperiodicity
    elems = profile.get("elements", [])
    flow = profile.get("flow_map", {}) or {}
    for a in elems:
        fixed, path = _iterate_flow(flow, a)
        if len(path) > len(set(path)):
            issues.append(f"Cycle detected in flow iterates from {a}: {path}")
            checks.append({"law": "aperiodic", "status": "fail", "counterexample": {"path": path}})
            continue
        if fixed != flow.get(fixed):
            issues.append(f"Iterates from {a} did not reach fixed point: {path}")
            checks.append({"law": "fixed_point", "status": "fail", "counterexample": {"path": path}})
        else:
            fixed_set.append(fixed)
    if not issues and all(c.get("law") != "flow_laws" for c in checks):
        checks.append({"law": "flow_laws", "status": "pass", "counterexample": None})
    evidence = assign_canonical_id(
        {
            "kind": "flow_laws_evidence",
            "profile_id": profile["id"],
            "status": status,
            "issues": issues,
            "checks": checks,
            "flow_fixed": fixed_set,
        }
    )
    if status == "fail":
        raise LoaderError(f"Flow law check failed: {issues[0]}")
    return [evidence]
