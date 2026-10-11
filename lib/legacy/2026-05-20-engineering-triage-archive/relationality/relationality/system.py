from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .graph import RelationalGraph
from .engine import execute_runbook
from .loaders import ObjectIndex, RunbookIndex, load_objects, load_runbooks
from .law_enforcement import validate_raw_object
from .validation import LawValidationError


def _select_singleton_by_kind(objects_by_kind: Dict[str, Dict[str, dict]], kind: str) -> dict:
    candidates = list(objects_by_kind.get(kind, {}).values())
    if not candidates:
        raise LawValidationError(f"no objects of required kind {kind!r} found for system construction")
    if len(candidates) > 1 and kind != "observation_carrier":
        # The current repository uses a single flow_map/nucleus_map/etc.
        # per system; multiple candidates would require explicit system
        # references, which are not present, so we reject to avoid
        # heuristic selection. Observation carriers are an exception: the
        # System interaction morphism accepts an external ObservationCarrier
        # payload, so persisted observation_carrier nodes serve only as
        # examples. In that case we select a deterministically minimal ID.
        raise LawValidationError(f"multiple objects of kind {kind!r} found; system is not uniquely determined")
    # When multiple observation_carrier nodes exist, select the one with
    # the minimal ID to keep construction deterministic without privileging
    # any particular command.
    return min(candidates, key=lambda obj: obj["id"])


def _select_observation_equivalence_for_system(system: dict, objects) -> dict:
    """
    Choose an observation_equivalence carrier covering the system's admissible observations.
    """
    measurement_frame = objects.by_id[system["measurement_frame_id"]]
    admissible = set(measurement_frame.get("admissible_observations") or [])
    eq_candidates = list(objects.by_kind.get("observation_equivalence", {}).values())
    if not eq_candidates:
        raise LawValidationError("no observation_equivalence objects found for system construction")
    if admissible:
        covering = [
            eq for eq in eq_candidates if admissible.issubset(set(eq.get("observation_ids") or []))
        ]
        if not covering:
            raise LawValidationError(
                "no observation_equivalence carrier covers the System's admissible observations"
            )
        return min(covering, key=lambda eq: eq["id"])
    return min(eq_candidates, key=lambda eq: eq["id"])


def build_system_subgraph_from_index(objects: ObjectIndex, system_id: str) -> RelationalGraph:
    """
    Construct the minimal closed subgraph for a persisted System.

    The subgraph includes:
    - the System carrier itself,
    - its referenced ProfileTopos, PhaseSpace, MeasurementFrame, Regime,
      Trace, FixedInvariants, and the distinguished FlowMap/NucleusMap
      named by the system object,
    - the observation_equivalence and observation_carrier objects required
      by the system_interaction pipeline.
    """
    system = objects.by_id.get(system_id)
    if system is None:
        raise KeyError(f"system {system_id} not found in loaded objects")
    if system.get("kind") != "system":
        raise LawValidationError(f"object {system_id} is not a system carrier")

    profile = objects.by_id.get(system["profile_topos_id"])
    phase_space = objects.by_id.get(system["phase_space_id"])
    measurement_frame = objects.by_id.get(system["measurement_frame_id"])
    regime = objects.by_id.get(system["regime_id"])
    trace = objects.by_id.get(system["trace_id"])
    fixed_invariants = objects.by_id.get(system["fixed_invariants_id"])
    flow_map = objects.by_id.get(system["flow_map_id"])
    nucleus_map = objects.by_id.get(system["nucleus_map_id"])
    if any(
        obj is None
        for obj in (
            profile,
            phase_space,
            measurement_frame,
            regime,
            trace,
            fixed_invariants,
            flow_map,
            nucleus_map,
        )
    ):
        raise LawValidationError("system references missing constituent carriers")
    # For each System, select an observation_equivalence carrier whose
    # observation_ids cover the System's admissible observations, when any
    # are declared by its MeasurementFrame.
    observation_equivalence = _select_observation_equivalence_for_system(system, objects)
    observation_carrier = _select_singleton_by_kind(objects.by_kind, "observation_carrier")

    graph = RelationalGraph()
    # Insert carriers in an order compatible with law enforcement gates.
    for obj in (
        profile,
        phase_space,
        measurement_frame,
        regime,
        trace,
        fixed_invariants,
        observation_equivalence,
        observation_carrier,
        flow_map,
        nucleus_map,
        system,
    ):
        graph.add_node(dict(obj))

    # Enrich the System subgraph with the term/typing layer tied to the
    # System's trace. This is a pure cut: we include exactly those
    # term-related carriers whose trace/context/typing references match the
    # System's trace and its induced term contexts, without introducing any
    # additional runtime state.
    trace_id = trace["id"]

    # Term contexts indexed by the System trace.
    context_ids: set[str] = set()
    for ctx in objects.by_kind.get("term_context", {}).values():
        if ctx.get("trace_id") == trace_id:
            graph.add_node(dict(ctx))
            context_ids.add(ctx["id"])

    # Terms living over those contexts or the System trace.
    term_ids: set[str] = set()
    for term in objects.by_kind.get("term", {}).values():
        if term.get("trace_id") == trace_id or term.get("context_id") in context_ids:
            graph.add_node(dict(term))
            term_ids.add(term["id"])

    # Typing judgments for those terms.
    judgment_ids: set[str] = set()
    for judgment in objects.by_kind.get("judgment", {}).values():
        if judgment.get("term_id") in term_ids:
            graph.add_node(dict(judgment))
            judgment_ids.add(judgment["id"])

    # Normal forms and evaluated judgments tied to the same term/judgment
    # layer.
    for nf in objects.by_kind.get("syntax_normal_form", {}).values():
        if nf.get("term_id") in term_ids:
            graph.add_node(dict(nf))
    for ev in objects.by_kind.get("evaluated_judgment", {}).values():
        if ev.get("judgment_id") in judgment_ids:
            graph.add_node(dict(ev))

    return graph


def build_system_subgraph(system_id: str) -> RelationalGraph:
    """
    Backwards-compatible wrapper that loads the object index and then
    delegates to :func:`build_system_subgraph_from_index`.
    """
    objects = load_objects()
    return build_system_subgraph_from_index(objects, system_id)


def run_system_interaction_with_indexes(
    objects: ObjectIndex,
    runbooks: RunbookIndex,
    system_id: str,
    observation_carrier_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute the system interaction morphism for a given System.

    This function:
    - loads objects and runbooks (with law enforcement),
    - builds the minimal System subgraph,
    - inserts the provided ObservationCarrier payload as a new node, and
    - runs the flow_nucleus_commutation and system_interaction runbooks
      in sequence.

    Returns a dictionary of updated carriers and evidence payloads:
    - phase_space
    - trace
    - observation
    - fixed_invariants
    - fix_flow_nucleus_iteration_evidence
    - commutation_evidence
    """
    # Validate the external observation carrier payload.
    if observation_carrier_payload.get("kind") != "observation_carrier":
        raise LawValidationError("run_system_interaction requires an observation_carrier payload")
    validate_raw_object(observation_carrier_payload)

    system = objects.by_id.get(system_id)
    if system is None:
        raise KeyError(f"system {system_id} not found in loaded objects")

    profile = objects.by_id[system["profile_topos_id"]]
    phase_space = objects.by_id[system["phase_space_id"]]
    measurement_frame = objects.by_id[system["measurement_frame_id"]]
    regime = objects.by_id[system["regime_id"]]
    trace = objects.by_id[system["trace_id"]]
    fixed_invariants = objects.by_id[system["fixed_invariants_id"]]
    flow_map = objects.by_id[system["flow_map_id"]]
    nucleus_map = objects.by_id[system["nucleus_map_id"]]

    # Build the minimal System subgraph from the provided object index so
    # that interaction is performed against the same carriers seen by the
    # caller (e.g. the process-global RelationalComputer).
    graph = build_system_subgraph_from_index(objects, system_id)
    # Add the external observation carrier as a fresh node in the AOG.
    graph.add_node(dict(observation_carrier_payload))

    # 1. Flow–nucleus commutation evidence.
    flow_commute_rb = next(iter(runbooks.by_name["flow_nucleus_commutation"].values()))
    commute_bindings = execute_runbook(
        graph,
        flow_commute_rb,
        initial_bindings={
            "flow_map": flow_map["id"],
            "nucleus_map": nucleus_map["id"],
        },
    )
    commutation_evidence_id = commute_bindings["commutation_evidence"]

    # 2. System interaction runbook.
    system_interaction_rb = next(iter(runbooks.by_name["system_interaction"].values()))
    interaction_bindings = execute_runbook(
        graph,
        system_interaction_rb,
        initial_bindings={
            "observation": observation_carrier_payload["id"],
            "profile_topos": profile["id"],
            "phase_space": phase_space["id"],
            "measurement_frame": measurement_frame["id"],
            "regime": regime["id"],
            "trace": trace["id"],
            "fixed_invariants": fixed_invariants["id"],
            "flow_map": flow_map["id"],
            "nucleus_map": nucleus_map["id"],
            "commutation_evidence": commutation_evidence_id,
        },
    )

    # Collect updated carriers and evidence from the final bindings.
    def _node(role: str) -> dict:
        node_id = interaction_bindings[role]
        return graph.nodes[node_id]

    result = {
        "phase_space": _node("phase_space"),
        "trace": _node("trace"),
        "observation": _node("observation"),
        "fixed_invariants": _node("fixed_invariants"),
        "fix_flow_nucleus_iteration_evidence": _node("fix_flow_nucleus_iteration_evidence"),
        "commutation_evidence": _node("commutation_evidence"),
    }
    return result


def run_system_interaction(system_id: str, observation_carrier_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper that loads indexes and delegates to
    :func:`run_system_interaction_with_indexes`.
    """
    objects = load_objects()
    runbooks = load_runbooks()
    return run_system_interaction_with_indexes(objects, runbooks, system_id, observation_carrier_payload)


def run_system_health_with_indexes(
    objects: ObjectIndex,
    runbooks: RunbookIndex,
    system_id: str,
) -> Dict[str, Any]:
    """
    Execute a deterministic diagnostic suite for the given system.

    The suite runs a fixed set of law-check runbooks on the system's
    carriers. It returns a report with per-runbook evidence payloads and
    an aggregate status of \"pass\" only when every runbook reports pass
    and executes without error.
    """
    system = objects.by_id.get(system_id)
    if system is None or system.get("kind") != "system":
        raise KeyError(f"system {system_id} not found in loaded objects")

    observation_equivalence = _select_observation_equivalence_for_system(system, objects)

    graph = RelationalGraph()
    # Insert carriers in an order compatible with node-level law enforcement.
    preload_kinds = [
        "profile_topos",
        "fixed_invariants",
        "phase_space",
        "measurement_frame",
        "observation_equivalence",
        "flow_map",
        "nucleus_map",
        "system",
    ]
    added_ids = set()
    for kind in preload_kinds:
        for obj in objects.by_kind.get(kind, {}).values():
            graph.add_node(dict(obj))
            added_ids.add(obj["id"])
    for obj in objects.by_id.values():
        if obj["id"] in added_ids:
            continue
        graph.add_node(dict(obj))

    diagnostics: List[Tuple[str, Dict[str, str]]] = [
        ("flow_laws_check", {"flow_map": system["flow_map_id"]}),
        ("nucleus_laws_check", {"nucleus_map": system["nucleus_map_id"]}),
        (
            "flow_nucleus_commutation",
            {"flow_map": system["flow_map_id"], "nucleus_map": system["nucleus_map_id"]},
        ),
        (
            "fixed_profile_check",
            {
                "profile_topos": system["profile_topos_id"],
                "flow_map": system["flow_map_id"],
                "nucleus_map": system["nucleus_map_id"],
            },
        ),
        (
            "trace_measurement_check",
            {"trace": system["trace_id"], "measurement_frame": system["measurement_frame_id"]},
        ),
        (
            "system_laws_check",
            {
                "system": system["id"],
                "profile_topos": system["profile_topos_id"],
                "phase_space": system["phase_space_id"],
                "measurement_frame": system["measurement_frame_id"],
                "regime": system["regime_id"],
                "trace": system["trace_id"],
                "fixed_invariants": system["fixed_invariants_id"],
                "flow_map": system["flow_map_id"],
                "nucleus_map": system["nucleus_map_id"],
                "observation_equivalence": observation_equivalence["id"],
            },
        ),
    ]

    results: List[Dict[str, Any]] = []
    overall_status = "pass"

    for name, bindings in diagnostics:
        rb = next(iter(runbooks.by_name[name].values()))
        try:
            output_bindings = execute_runbook(graph, rb, initial_bindings=bindings)
        except Exception as exc:
            overall_status = "fail"
            results.append({"runbook": name, "status": "fail", "error": str(exc)})
            continue

        evidence_payloads: Dict[str, Any] = {}
        runbook_status = "pass"
        for spec in rb.get("outputs", []):
            role = spec["role"]
            node_id = output_bindings[role]
            node = graph.nodes[node_id]
            evidence_payloads[role] = node
            if node.get("status") and node.get("status") != "pass":
                runbook_status = "fail"
        if runbook_status == "fail":
            overall_status = "fail"
        results.append({"runbook": name, "status": runbook_status, "evidence": evidence_payloads})

    return {"status": overall_status, "results": results}


def run_system_health(system_id: str) -> Dict[str, Any]:
    """
    Wrapper that loads indexes and delegates to
    :func:`run_system_health_with_indexes`.
    """
    objects = load_objects()
    runbooks = load_runbooks()
    return run_system_health_with_indexes(objects, runbooks, system_id)
