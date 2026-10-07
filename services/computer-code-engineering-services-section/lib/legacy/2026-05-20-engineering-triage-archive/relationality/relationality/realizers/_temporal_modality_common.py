from __future__ import annotations

from typing import Dict, List, Mapping, Tuple

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_object


def _load_profile_and_fixed(graph, flow_map: Mapping[str, object], nucleus_map: Mapping[str, object], fixed_invariants: Mapping[str, object]) -> Tuple[dict, List[str], List[str], dict]:
    """
    Resolve the shared profile_topos carrier and fixed invariants.

    Ensures:
    - flow_map and nucleus_map share the same carrier and element set;
    - fixed_invariants elements are a subset of the carrier elements.
    """
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("temporal modality requires flow_map input of kind 'flow_map'")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("temporal modality requires nucleus_map input of kind 'nucleus_map'")
    if fixed_invariants.get("kind") != "fixed_invariants":
        raise LawValidationError("temporal modality requires fixed_invariants input of kind 'fixed_invariants'")

    carrier_id_flow = flow_map.get("carrier_id")
    carrier_id_nucleus = nucleus_map.get("carrier_id")
    if not isinstance(carrier_id_flow, str) or not isinstance(carrier_id_nucleus, str):
        raise LawValidationError("flow_map and nucleus_map must declare carrier_id")
    if carrier_id_flow != carrier_id_nucleus:
        raise LawValidationError("flow_map and nucleus_map must share the same carrier_id")
    profile = graph.nodes.get(carrier_id_flow)
    if profile is None:
        raise LawValidationError(f"profile_topos {carrier_id_flow!r} referenced by flow/nucleus not found in graph")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("temporal modality carrier must be a profile_topos")

    basis: List[str] = list(profile.get("elements", []))
    if not basis:
        raise LawValidationError("profile_topos must provide a non-empty elements basis for temporal modality")
    carrier_elements = set(basis)
    flow_elements = set(flow_map.get("elements", []))
    nucleus_elements = set(nucleus_map.get("elements", []))
    if carrier_elements != flow_elements or carrier_elements != nucleus_elements:
        raise LawValidationError(
            "flow_map.elements, nucleus_map.elements, and profile_topos.elements must agree for temporal modality"
        )

    fixed_elements: List[str] = list(fixed_invariants.get("elements", []))
    fixed_set = set(fixed_elements)
    if not fixed_set:
        raise LawValidationError("fixed_invariants must provide a non-empty elements set for temporal modality")
    if not fixed_set.issubset(carrier_elements):
        raise LawValidationError("fixed_invariants.elements must be a subset of profile_topos.elements")

    # Fixed points must be jointly fixed by flow and nucleus: for every
    # element e in fixed_invariants, F(e) = e and ν(e) = e. This enforces
    # that the supplied fixed set really is Fix(F,ν), not an arbitrary
    # subset of the lattice.
    flow_table = flow_map.get("flow_table", {})
    nucleus_table = nucleus_map.get("nucleus_table", {})
    for elt in fixed_elements:
        f_elt = flow_table.get(elt)
        n_elt = nucleus_table.get(elt)
        if f_elt != elt or n_elt != elt:
            raise LawValidationError(
                "fixed_invariants elements must be jointly fixed by flow and nucleus for temporal modality"
            )

    # Flow and nucleus must commute on the carrier: F∘ν = ν∘F pointwise.
    # We reuse the flow_nucleus_commutation diagnostic realizer as a hard
    # gate here, ignoring its graph mutations and inspecting only the
    # evidence node.
    from relationality.realizers.flow_nucleus_commutation import (  # type: ignore[import]
        realize as flow_nucleus_commutation_realizer,
    )

    comm_output = flow_nucleus_commutation_realizer(
        graph,
        {"flow_map": dict(flow_map), "nucleus_map": dict(nucleus_map)},
        {
            "runbook": {
                "id": "0" * 64,
                "name": "flow_nucleus_commutation",
            },
            "step": {"step_index": 0},
        },
    )
    if not comm_output.nodes:
        raise LawValidationError("flow_nucleus_commutation did not emit evidence node for temporal modality gate")
    comm_evidence = comm_output.nodes[0]
    validate_object(comm_evidence)
    if comm_evidence.get("status") != "pass":
        raise LawValidationError("flow and nucleus must commute to construct temporal modalities")

    order = profile.get("order", {})

    # Optional sheaf/presheaf gate: when a sheaf or presheaf carrier is
    # present in the graph, enforce alignment with the profile_topos via
    # SheafProfileConsistency and enforce the SheafCondition via the
    # sheafification_evidence realizer (when a presheaf + site are
    # available). This ties temporal modalities to the ambient sheaf
    # semantics without requiring sheaf data in the minimal systems used
    # by existing tests.
    for node in getattr(graph, "nodes", {}).values():
        kind = node.get("kind")
        if kind not in {"sheaf", "presheaf"}:
            continue
        from relationality.realizers.sheaf_profile_consistency import (  # local import to avoid cycles
            realize as sheaf_profile_consistency_realizer,
        )

        output = sheaf_profile_consistency_realizer(
            graph,
            {"sheaf_or_presheaf": dict(node), "profile_topos": dict(profile)},
            {"runbook": {"id": "0" * 64, "name": "sheaf_profile_consistency"}, "step": {"step_index": 0}},
        )
        if not output.nodes:
            raise LawValidationError("sheaf_profile_consistency did not emit evidence node")
        evidence = output.nodes[0]
        validate_object(evidence)
        if evidence.get("status") != "pass":
            raise LawValidationError(
                "sheaf_profile_consistency evidence reports failure for temporal modality carrier"
            )

        # When the carrier is a presheaf and its site is present in the
        # graph, also require that the sheafification_evidence realizer
        # reports a passing SheafCondition witness. This ensures that
        # temporal modalities only see presheaves that already satisfy
        # the internal sheaf laws enforced by the acts.
        if kind == "presheaf":
            site_id = node.get("site_id")
            if isinstance(site_id, str):
                site = graph.nodes.get(site_id)
                if site is not None and site.get("kind") == "presheaf_site":
                    from relationality.realizers.sheafification_evidence import (  # type: ignore[import]
                        realize as sheafification_evidence_realizer,
                    )

                    ev_output = sheafification_evidence_realizer(
                        graph,
                        {"presheaf_site": dict(site), "presheaf": dict(node)},
                        {
                            "runbook": {
                                "id": "0" * 64,
                                "name": "sheafification_evidence",
                            },
                            "step": {"step_index": 0},
                        },
                    )
                    if not ev_output.nodes:
                        raise LawValidationError("sheafification_evidence did not emit evidence node")
                    sheaf_ev = ev_output.nodes[0]
                    validate_object(sheaf_ev)
                    if sheaf_ev.get("status") != "pass":
                        raise LawValidationError(
                            "sheafification_evidence reports failure for temporal modality presheaf carrier"
                        )
        break

    return profile, basis, fixed_elements, order


def _leq(order: Mapping[str, List[str]], a: str, b: str) -> bool:
    """
    Order relation: a <= b iff b is listed in order[a].
    """
    return b in order.get(a, [])


def _greatest_fixed_leq(x: str, fixed_elements: List[str], order: Mapping[str, List[str]]) -> str:
    candidates = [s for s in fixed_elements if _leq(order, s, x)]
    if not candidates:
        raise LawValidationError(f"no fixed invariant element <= {x!r} for always modality")
    # Greatest elements: those not strictly below another candidate.
    maximal: List[str] = []
    for s in candidates:
        if not any(s != t and _leq(order, s, t) for t in candidates):
            maximal.append(s)
    if len(maximal) != 1:
        raise LawValidationError(
            f"fixed invariants do not form a sublattice below {x!r}: multiple maximal elements {maximal!r}"
        )
    return maximal[0]


def _least_fixed_geq(x: str, fixed_elements: List[str], order: Mapping[str, List[str]]) -> str:
    candidates = [s for s in fixed_elements if _leq(order, x, s)]
    if not candidates:
        raise LawValidationError(f"no fixed invariant element >= {x!r} for eventually modality")
    # Least elements: those not strictly above another candidate.
    minimal: List[str] = []
    for s in candidates:
        if not any(s != t and _leq(order, t, s) for t in candidates):
            minimal.append(s)
    if len(minimal) != 1:
        raise LawValidationError(
            f"fixed invariants do not form a sublattice above {x!r}: multiple minimal elements {minimal!r}"
        )
    return minimal[0]


def _compute_temporal_tables(
    basis: List[str],
    fixed_elements: List[str],
    order: Mapping[str, List[str]],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    always_table: Dict[str, str] = {}
    eventually_table: Dict[str, str] = {}
    for x in basis:
        always_table[x] = _greatest_fixed_leq(x, fixed_elements, order)
        eventually_table[x] = _least_fixed_geq(x, fixed_elements, order)
    return always_table, eventually_table


def _compute_residuation_table(
    basis: List[str],
    always_table: Mapping[str, str],
    eventually_table: Mapping[str, str],
    order: Mapping[str, List[str]],
) -> Tuple[List[Dict[str, object]], bool, Dict[str, object] | None]:
    """
    Build the residuation table for the adjunction:

        always(x) <= y   <=>   x <= eventually(y)

    Returns (table, all_pass, counterexample).
    """
    table: List[Dict[str, object]] = []
    all_pass = True
    counterexample: Dict[str, object] | None = None
    for x in basis:
        ax = always_table[x]
        for y in basis:
            ey = eventually_table[y]
            lhs = _leq(order, ax, y)
            rhs = _leq(order, x, ey)
            entry = {
                "x": x,
                "y": y,
                "always_x": ax,
                "eventually_y": ey,
                "lhs": lhs,
                "rhs": rhs,
            }
            table.append(entry)
            if all_pass and lhs != rhs:
                all_pass = False
                counterexample = dict(entry)
    return table, all_pass, counterexample


def build_temporal_modality(
    graph,
    flow_map: Mapping[str, object],
    nucleus_map: Mapping[str, object],
    fixed_invariants: Mapping[str, object],
    operator: str,
) -> RealizerOutput:
    """
    Shared implementation for always_modality and eventually_modality.

    Computes the temporal_modality carrier and residuation evidence from
    F, ν, and Fix(F,ν) encoded as flow_map, nucleus_map, and fixed_invariants.
    """
    profile, basis, fixed_elements, order = _load_profile_and_fixed(
        graph, flow_map, nucleus_map, fixed_invariants
    )

    always_table, eventually_table = _compute_temporal_tables(basis, fixed_elements, order)

    temporal = {
        "kind": "temporal_modality",
        "basis": basis,
        "always_table": always_table,
        "eventually_table": eventually_table,
        "flow_ref": flow_map["id"],
        "nucleus_ref": nucleus_map["id"],
        "fix_ref": fixed_invariants["id"],
        "act_ref": "CloseTemporally",
    }
    ensure_id_coherence(temporal)

    residuation_table, all_pass, counterexample = _compute_residuation_table(
        basis, always_table, eventually_table, order
    )
    evidence: Dict[str, object] = {
        "kind": "temporal_modality_evidence",
        "temporal_modality_id": temporal["id"],
        "residuation_table": residuation_table,
        "status": "pass" if all_pass else "fail",
        "act_ref": "CloseTemporally",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    # Edges are parameterized by the operator name to satisfy runbook typing.
    edges = [
        {
            "operator": operator,
            "src": flow_map["id"],
            "tgt": temporal["id"],
        },
        {
            "operator": operator,
            "src": nucleus_map["id"],
            "tgt": temporal["id"],
        },
        {
            "operator": operator,
            "src": fixed_invariants["id"],
            "tgt": temporal["id"],
        },
        {
            "operator": operator,
            "src": temporal["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[temporal, evidence],
        edges=edges,
        bindings={
            "temporal_modality": temporal["id"],
            "temporal_modality_evidence": evidence["id"],
        },
    )


def check_close_temporally(
    graph,
    flow_map: Mapping[str, object],
    nucleus_map: Mapping[str, object],
    fixed_invariants: Mapping[str, object],
) -> RealizerOutput:
    """
    Diagnostic variant used by close_temporally_check.

    Recomputes the temporal tables and residuation evidence without emitting
    a temporal_modality carrier.
    """
    profile, basis, fixed_elements, order = _load_profile_and_fixed(
        graph, flow_map, nucleus_map, fixed_invariants
    )
    always_table, eventually_table = _compute_temporal_tables(basis, fixed_elements, order)
    residuation_table, all_pass, counterexample = _compute_residuation_table(
        basis, always_table, eventually_table, order
    )
    # Build a deterministic temporal_modality_id by reusing the same
    # construction as build_temporal_modality but without emitting the
    # carrier node. This maintains referential alignment between evidence
    # and the underlying modality.
    temporal_stub = {
        "kind": "temporal_modality",
        "basis": basis,
        "always_table": always_table,
        "eventually_table": eventually_table,
        "flow_ref": flow_map["id"],
        "nucleus_ref": nucleus_map["id"],
        "fix_ref": fixed_invariants["id"],
        "act_ref": "CloseTemporally",
    }
    ensure_id_coherence(temporal_stub)

    evidence: Dict[str, object] = {
        "kind": "temporal_modality_evidence",
        "temporal_modality_id": temporal_stub["id"],
        "residuation_table": residuation_table,
        "status": "pass" if all_pass else "fail",
        "act_ref": "CloseTemporallyCheck",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "close_temporally_check",
            "src": flow_map["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "close_temporally_check",
            "src": nucleus_map["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "close_temporally_check",
            "src": fixed_invariants["id"],
            "tgt": evidence["id"],
        },
    ]
    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"temporal_modality_evidence": evidence["id"]},
    )
