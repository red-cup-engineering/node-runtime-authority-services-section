"""Check judgment lattice laws on a profile payload."""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def _table_value(table: dict, a: str, b: str) -> str:
    try:
        return table[a][b]
    except Exception as exc:  # pragma: no cover - converted to LoaderError
        raise LoaderError(f"Missing table entry for ({a},{b})") from exc


def _reachable(order: Dict[str, List[str]], start: str) -> Set[str]:
    """Return all elements >= start using the order adjacency."""
    seen: Set[str] = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(order.get(cur, []))
    return seen


def has_judgment_tables(carrier: dict) -> bool:
    """Return True if the carrier includes all lattice tables required for checks."""
    required = ("elements", "order", "meet", "join", "imply")
    return all(k in carrier for k in required)


def check_judgment_laws(carrier: dict) -> Tuple[List[str], List[dict]]:
    """Return (issues, checks) for judgment lattice laws on a finite carrier."""
    missing = [field for field in ("elements", "order", "meet", "join", "imply") if field not in carrier]
    issues: List[str] = []
    checks: List[dict] = []
    if missing:
        issues.append(f"Missing lattice fields: {', '.join(missing)}")
        checks.append({"law": "total", "status": "fail", "counterexample": {"missing": missing}})
        return issues, checks

    elems = carrier.get("elements", [])
    bottom = carrier.get("bottom")
    top = carrier.get("top")
    negate = carrier.get("negate_map")
    classifier = carrier.get("classifier")
    limits = carrier.get("limits")
    meet = carrier.get("meet", {})
    join = carrier.get("join", {})
    imply = carrier.get("imply", {})
    order = carrier.get("order", {})

    # Require explicit order adjacency for every element and range ⊆ elements.
    missing_order_keys = [e for e in elems if e not in order]
    if missing_order_keys:
        issues.append(f"Order missing entries for: {', '.join(missing_order_keys)}")
        checks.append({"law": "order_total", "status": "fail", "counterexample": {"missing": missing_order_keys}})
    for src, targets in order.items():
        if not isinstance(targets, list):
            issues.append(f"Order entry for {src} is not a list")
            checks.append({"law": "order_shape", "status": "fail", "counterexample": {"src": src, "targets": targets}})
            continue
        extraneous = [t for t in targets if t not in elems]
        if extraneous:
            issues.append(f"Order targets outside carrier for {src}: {extraneous}")
            checks.append({"law": "order_range", "status": "fail", "counterexample": {"src": src, "targets": extraneous}})

    def leq(x: str, y: str) -> bool:
        return y in _reachable(order, x)

    # Bounds and negate presence
    if bottom is None or bottom not in elems:
        issues.append("Missing or invalid bottom")
        checks.append({"law": "bounds", "status": "fail", "counterexample": {"bottom": bottom}})
    if top is None or top not in elems:
        issues.append("Missing or invalid top")
        checks.append({"law": "bounds", "status": "fail", "counterexample": {"top": top}})
    if negate is None or not isinstance(negate, dict):
        issues.append("Missing negate_map")
        checks.append({"law": "negate_total", "status": "fail", "counterexample": None})
    else:
        missing_neg = [e for e in elems if e not in negate]
        if missing_neg:
            issues.append(f"Negate map missing entries for: {missing_neg}")
            checks.append({"law": "negate_total", "status": "fail", "counterexample": {"missing": missing_neg}})
        extraneous_neg = [k for k in negate if k not in elems]
        if extraneous_neg:
            issues.append(f"Negate map has extraneous keys: {extraneous_neg}")
            checks.append({"law": "negate_range", "status": "fail", "counterexample": {"extraneous": extraneous_neg}})

    # Classifier / limits presence (earned elsewhere; here we only check shape if present)
    if classifier and ("truth" not in classifier or "false" not in classifier):
        issues.append("Classifier missing truth/false")
        checks.append({"law": "classifier", "status": "fail", "counterexample": classifier})
    if limits is None or not isinstance(limits, dict):
        if top is not None:
            limits = {"terminal": top}
        else:
            issues.append("Missing limits/terminal")
            checks.append({"law": "limits", "status": "fail", "counterexample": limits})
    elif "terminal" not in limits:
        issues.append("Missing limits/terminal")
        checks.append({"law": "limits", "status": "fail", "counterexample": limits})
    if limits:
        terminal = limits.get("terminal")
        if terminal not in elems:
            issues.append("Limits terminal not in carrier elements")
            checks.append({"law": "limits_terminal", "status": "fail", "counterexample": {"terminal": terminal}})
        if top is not None and terminal is not None and terminal != top:
            issues.append("Limits terminal does not match top")
            checks.append(
                {"law": "limits_terminal", "status": "fail", "counterexample": {"terminal": terminal, "top": top}}
            )
        pullbacks = limits.get("pullbacks") or []
        for idx, pb in enumerate(pullbacks):
            apex, left, right = pb.get("apex"), pb.get("left"), pb.get("right")
            missing_pb = [name for name, val in (("apex", apex), ("left", left), ("right", right)) if val is None]
            if missing_pb:
                issues.append(f"Pullback {idx} missing fields: {missing_pb}")
                checks.append({"law": "pullback_shape", "status": "fail", "counterexample": {"index": idx}})
                continue
            for label, val in (("apex", apex), ("left", left), ("right", right)):
                if val not in elems:
                    issues.append(f"Pullback {idx} {label} not in carrier")
                    checks.append(
                        {
                            "law": "pullback_elements",
                            "status": "fail",
                            "counterexample": {"index": idx, "label": label, "value": val},
                        }
                    )
                    break

    # Order properties: reflexive, antisymmetric
    for a in elems:
        reachable = _reachable(order, a)
        if a not in reachable:
            issues.append(f"Reflexivity fail for {a}")
            checks.append({"law": "reflexive", "status": "fail", "counterexample": {"a": a}})
        for b in elems:
            if a != b and b in reachable and a in _reachable(order, b):
                issues.append(f"Antisymmetry fail: {a}<= {b} and {b}<= {a}")
                checks.append({"law": "antisymmetric", "status": "fail", "counterexample": {"a": a, "b": b}})

    for a in elems:
        for b in elems:
            m = _table_value(meet, a, b)
            j = _table_value(join, a, b)
            if m not in elems or j not in elems:
                msg = f"Meet/Join result not in elements for ({a},{b})"
                issues.append(msg)
                checks.append({"law": "closure", "status": "fail", "counterexample": {"a": a, "b": b}})
            # commutativity
            if m != _table_value(meet, b, a):
                msg = f"Meet not commutative for ({a},{b})"
                issues.append(msg)
                checks.append({"law": "meet_commutative", "status": "fail", "counterexample": {"a": a, "b": b}})
            if j != _table_value(join, b, a):
                msg = f"Join not commutative for ({a},{b})"
                issues.append(msg)
                checks.append({"law": "join_commutative", "status": "fail", "counterexample": {"a": a, "b": b}})
            # absorption
            if _table_value(join, a, m) != a:
                issues.append(f"Absorption join failed for {a} with meet")
                checks.append({"law": "absorption", "status": "fail", "counterexample": {"a": a, "b": b}})
            if _table_value(meet, a, j) != a:
                issues.append(f"Absorption meet failed for {a} with join")
                checks.append({"law": "absorption", "status": "fail", "counterexample": {"a": a, "b": b}})

    # Meet/join as glb/lub
    for a in elems:
        for b in elems:
            m = _table_value(meet, a, b)
            j = _table_value(join, a, b)
            if not leq(m, a) or not leq(m, b):
                issues.append(f"Meet not below operands for ({a},{b})")
                checks.append({"law": "meet_glb", "status": "fail", "counterexample": {"a": a, "b": b, "m": m}})
            for x in elems:
                if leq(x, a) and leq(x, b) and not leq(x, m):
                    issues.append(f"Meet not greatest lower bound for ({a},{b}) vs {x}")
                    checks.append({"law": "meet_glb", "status": "fail", "counterexample": {"a": a, "b": b, "x": x, "m": m}})
                    break
            if not leq(a, j) or not leq(b, j):
                issues.append(f"Join not above operands for ({a},{b})")
                checks.append({"law": "join_lub", "status": "fail", "counterexample": {"a": a, "b": b, "j": j}})
            for x in elems:
                if leq(a, x) and leq(b, x) and not leq(j, x):
                    issues.append(f"Join not least upper bound for ({a},{b}) vs {x}")
                    checks.append({"law": "join_lub", "status": "fail", "counterexample": {"a": a, "b": b, "x": x, "j": j}})
                    break

    # Implication adjunction: a ∧ x <= b iff x <= (a => b)
    for a in elems:
        for b in elems:
            candidate = _table_value(imply, a, b)
            if not leq(_table_value(meet, a, candidate), b):
                issues.append(f"Implication adjunction fail: a∧(a=>b) !<= b for ({a},{b})")
                checks.append({"law": "adjunction", "status": "fail", "counterexample": {"a": a, "b": b, "imp": candidate}})
            for x in elems:
                if leq(_table_value(meet, a, x), b) and not leq(x, candidate):
                    issues.append(f"Implication not maximal for ({a},{b}); x={x} exceeds candidate")
                    checks.append({"law": "adjunction", "status": "fail", "counterexample": {"a": a, "b": b, "x": x, "imp": candidate}})
                    break

    if not issues:
        checks.append({"law": "judgment_laws", "status": "pass", "counterexample": None})
    return issues, checks


def ensure_judgment_laws(carrier: dict) -> None:
    """Raise LoaderError if the carrier fails judgment lattice laws."""
    issues, _ = check_judgment_laws(carrier)
    if issues:
        raise LoaderError(f"Judgment lattice law failure: {issues[0]}")


def judgment_laws(graph, payloads: List[dict], ctx=None):
    """Return evidence if the profile satisfies basic judgment lattice properties."""
    if len(payloads) != 1 or payloads[0].get("kind") != "profile":
        raise LoaderError("judgment_laws expects a single profile payload")
    profile = payloads[0]
    issues, checks = check_judgment_laws(profile)
    status = "pass" if not issues else "fail"
    evidence = assign_canonical_id(
        {"kind": "judgment_laws_evidence", "status": status, "issues": issues, "checks": checks}
    )
    if status == "fail":
        raise LoaderError(f"Judgment lattice law check failed: {issues[0]}")
    return [evidence]
