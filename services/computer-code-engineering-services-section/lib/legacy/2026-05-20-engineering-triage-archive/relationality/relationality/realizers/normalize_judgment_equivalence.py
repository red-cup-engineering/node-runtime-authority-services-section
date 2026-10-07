"""Normalize judgment equivalence placeholder."""

from __future__ import annotations

from typing import Dict, List, Set

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def _validate_pairs(pairs: List[List[str]]) -> List[str]:
    issues: List[str] = []
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            issues.append(f"Invalid pair structure: {pair}")
            continue
        a, b = pair
        if not isinstance(a, str) or not isinstance(b, str):
            issues.append(f"Non-string judgment in pair: {pair}")
    return issues


def _normalize_pairs(pairs: List[List[str]]) -> List[List[str]]:
    """Symmetric/transitive closure of judgment equivalence pairs."""
    # Build adjacency
    adj: Dict[str, Set[str]] = {}
    for a, b in pairs:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    # Ensure reflexivity
    for node in list(adj.keys()):
        adj[node].add(node)
    # Compute components
    visited: Set[str] = set()
    normalized: Set[tuple] = set()
    for node in sorted(adj):
        if node in visited:
            continue
        stack = [node]
        comp: Set[str] = set()
        while stack:
            cur = stack.pop()
            if cur in comp:
                continue
            comp.add(cur)
            visited.add(cur)
            stack.extend(adj.get(cur, []))
        comp_list = sorted(comp)
        for i, a in enumerate(comp_list):
            for b in comp_list[i:]:
                normalized.add((a, b))
    return [[a, b] for a, b in sorted(normalized)]


def normalize_judgment_equivalence(graph, payloads: List[dict], ctx=None):
    if len(payloads) != 1 or payloads[0].get("kind") != "judgment_equivalence":
        raise LoaderError("normalize_judgment_equivalence expects judgment_equivalence")
    eq = payloads[0]
    pairs = eq.get("pairs", [])
    issues = _validate_pairs(pairs)
    if issues:
        raise LoaderError(f"Invalid judgment_equivalence pairs: {issues[0]}")
    normalized_pairs = _normalize_pairs(pairs)
    evidence = assign_canonical_id(
        {
            "kind": "judgment_equivalence_evidence",
            "status": "pass",
            "issues": [],
            "checks": [{"law": "judgment_equivalence_closure", "status": "pass", "counterexample": None}],
        }
    )
    normalized = {
        "kind": "judgment_equivalence",
        "pairs": normalized_pairs,
        "evidence_ids": [evidence["id"]],
    }
    normalized = assign_canonical_id(normalized)
    return [normalized, evidence]
