from __future__ import annotations

from typing import Dict, List, Mapping, Set

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.observation_equivalence_utils import canonicalize_observation_element
from relationality.validation import LawValidationError, validate_trace, validate_observation_equivalence


def _collect_equivalence_classes(eq: Mapping[str, object]) -> Mapping[str, List[str]]:
    """
    Build a mapping representative -> full equivalence class list.

    The observation_equivalence carrier may provide equivalence_classes
    explicitly; when present, these define the classes. We map each element
    in a class to its canonical representative using the equivalence_table.
    """
    classes: Mapping[str, List[str]] | None = None
    raw_classes = eq.get("equivalence_classes")
    if isinstance(raw_classes, list) and raw_classes:
        table = eq.get("equivalence_table") or {}
        rep_to_class: Dict[str, List[str]] = {}
        for cls in raw_classes:
            if not isinstance(cls, list) or not cls:
                raise LawValidationError("observation_equivalence.equivalence_classes must be non-empty lists")
            # Use the canonical representative of the first element as the
            # class representative; validate all members map there.
            first = cls[0]
            rep_first = table.get(first)
            if not isinstance(rep_first, str):
                raise LawValidationError("equivalence_table must map class elements to canonical representatives")
            for member in cls:
                rep_member = table.get(member)
                if rep_member != rep_first:
                    raise LawValidationError(
                        "equivalence_classes and equivalence_table must induce the same partition of observation_ids"
                    )
            rep_to_class[rep_first] = list(cls)
        classes = rep_to_class
    return classes or {}


def _linear_extension_from_carrier(graph, elements: Set[str]) -> List[str]:
    """
    Compute a deterministic linear extension of a finite subset of a carrier lattice.

    The ambient carrier is discovered by scanning graph.nodes for a profile_topos
    or phase_space whose elements/states contain the given subset and whose
    order table is available. We then perform a topological sort with
    tie-breaking determined by the carrier's own element enumeration.
    """
    nodes = getattr(graph, "nodes", {})
    candidates: List[Mapping[str, object]] = []
    for node in nodes.values():
        kind = node.get("kind")
        if kind == "profile_topos":
            carrier_elements = set(node.get("elements", []))
        elif kind == "phase_space":
            carrier_elements = set(node.get("states", []))
        else:
            continue
        if elements.issubset(carrier_elements):
            candidates.append(node)
    if not candidates:
        # Fallback: deterministic ordering by element string when no ambient
        # carrier is present. This remains lawful but loses lattice-informed
        # structure.
        return sorted(elements)
    # Deterministically choose the carrier with minimal id when present.
    carrier = min(candidates, key=lambda c: c.get("id", ""))
    kind = carrier.get("kind")
    if kind == "profile_topos":
        enumeration = list(carrier.get("elements", []))
    else:
        enumeration = list(carrier.get("states", []))
    order_table = carrier.get("order") or {}
    # Restrict order to the subset.
    preds: Dict[str, Set[str]] = {e: set() for e in elements}
    for x in elements:
        uppers = set(order_table.get(x, []))
        lowers = {y for y in elements if x in order_table.get(y, [])}
        # Standard partial order convention: order[x] lists elements >= x.
        # Predecessors of x are those y != x with x in order[y].
        preds[x] = {y for y in lowers if y != x}
    result: List[str] = []
    remaining: Set[str] = set(elements)
    while remaining:
        # Minimal elements: those with no predecessors within remaining.
        minimal = [e for e in remaining if not (preds[e] & remaining)]
        if not minimal:
            raise LawValidationError("trace_reentry linear extension failed: cycle detected in carrier order")
        # Tie-break minimal elements according to carrier enumeration.
        minimal.sort(key=lambda e: enumeration.index(e) if e in enumeration else len(enumeration))
        chosen = minimal[0]
        result.append(chosen)
        remaining.remove(chosen)
    return result


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    trace_reentry realizer.

    Inputs
    ------
    trace:
        Trace carrier whose elements are recognitions in the ambient lattice.

    Semantics
    ---------
    Realizes TraceReentryClosure by closing the trace under the ambient
    observation equivalence relation and emitting both:
    - a new trace whose elements form an equivalence-class-closed subset; and
    - a reentry_trace_evidence node describing the closure and its status.

    Closure condition (full equivalence-class closure):
    For every element e in the original trace and every y equivalent to e in
    the observation_equivalence carrier, y must appear in the new trace.
    """
    trace = inputs.get("trace")
    if trace is None:
        raise KeyError("trace_reentry requires 'trace' input")
    if trace.get("kind") != "trace":
        raise LawValidationError("trace_reentry input must have kind 'trace'")

    validate_trace(trace)
    elements: List[str] = list(trace.get("elements", []))
    if not elements:
        raise LawValidationError("trace_reentry requires a non-empty trace")

    # Locate the observation_equivalence carrier governing these elements.
    # We require a single observation_equivalence whose observation_ids
    # contain all trace elements.
    nodes = getattr(graph, "nodes", {})
    eq_candidates: List[dict] = []
    for node in nodes.values():
        if node.get("kind") != "observation_equivalence":
            continue
        obs_ids = set(node.get("observation_ids", []))
        if set(elements).issubset(obs_ids):
            eq_candidates.append(node)
    if not eq_candidates:
        raise LawValidationError(
            "trace_reentry requires an observation_equivalence carrier whose observation_ids "
            "cover all trace elements"
        )
    if len(eq_candidates) > 1:
        raise LawValidationError(
            "trace_reentry found multiple observation_equivalence carriers covering the trace elements"
        )
    eq = eq_candidates[0]
    validate_observation_equivalence(eq)

    classes_by_rep = _collect_equivalence_classes(eq)
    eq_table: Mapping[str, str] = eq.get("equivalence_table") or {}

    closed_set: Set[str] = set(elements)
    reentry_steps: List[dict] = []
    counterexample = None

    # For each element, identify its representative and full class, then
    # ensure the new trace will contain the entire class.
    for elt in elements:
        rep, _ = canonicalize_observation_element(eq, elt)
        eq_class = classes_by_rep.get(rep)
        if not eq_class:
            # Fall back to the equivalence_table image: class is all y with
            # table[y] == rep.
            eq_class = [y for y, r in eq_table.items() if r == rep]
        for member in eq_class:
            closed_set.add(member)
        reentry_steps.append(
            {
                "element": elt,
                "class_representative": rep,
                "equivalence_class": list(eq_class),
            }
        )

    # Construct a canonical linear extension of the closed set using the
    # ambient lattice order when available.
    new_elements = _linear_extension_from_carrier(graph, closed_set)
    new_trace = {
        "kind": "trace",
        "elements": new_elements,
        "head": new_elements[0],
        "tail": new_elements[1:],
    }
    ensure_id_coherence(new_trace)

    evidence_status = "pass"
    if counterexample is not None:
        evidence_status = "fail"

    evidence = {
        "kind": "reentry_trace_evidence",
        "trace_id": new_trace["id"],
        "reentry_steps": reentry_steps,
        "status": evidence_status,
        "act_ref": "TraceReentryClosure",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "trace_reentry",
            "src": trace["id"],
            "tgt": new_trace["id"],
        },
        {
            "operator": "trace_reentry",
            "src": new_trace["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[new_trace, evidence],
        edges=edges,
        bindings={"trace": new_trace["id"], "reentry_trace_evidence": evidence["id"]},
    )

