from __future__ import annotations

"""
Law enforcement gates for carriers and runbooks.

This module sits *above* :mod:`relationality.validation`:

- :mod:`relationality.validation` is responsible for schema validation
  and single-carrier (local) law checks.
- This module enforces **graph-level** and **runbook-level** laws that
  depend on multiple carriers and the AOG wiring (Flow/Nucleus/System
  laws, runbook sequencing laws, geometry_profile, reducibility
  candidates, etc.).

In particular, it promotes law-check runbooks into hard gates:

- ``flow_laws_check``       → guards flow_map carriers,
- ``nucleus_laws_check``    → guards nucleus_map carriers,
- ``system_laws_check``     → guards system carriers,
- ``runbook_laws_check``    → guards persisted runbooks.

Helpers here accept plain payloads and a graph-like object providing a
``nodes`` mapping when needed. On any failed law they raise
``LawValidationError``; callers must treat these as hard errors and
avoid mutating the AOG. Loaders and boot-time helpers must *not* import
or call these gates; they are for runtime and post-boot diagnostics.
"""

from typing import Dict, Mapping, MutableMapping

from .canonical import ensure_id_coherence
from .local_graph import LocalGraph, execute_runbook_local
from .schemas import load_schema
from .realizers import resolve_realizer
from .validation import LawValidationError, validate_object


def _summarize_counterexample(evidence: Mapping[str, object]) -> str:
    ce = evidence.get("counterexample")
    if not isinstance(ce, Mapping):
        return ""
    law = ce.get("law")
    if law:
        return f" (first failed law: {law})"
    return ""


def execute_law_runbook(
    runbook_name: str,
    inputs: Mapping[str, Mapping[str, object]],
) -> Dict[str, dict]:
    """
    Execute a law-check runbook on a fresh local AOG view.

    This is the *runtime* law harness: it routes Flow/Nucleus/System and
    related law enforcement through the same runbooks and realizers used
    everywhere else in the machine.

    ``inputs`` maps runbook input roles to carrier payloads; the helper
    seeds a temporary :class:`LocalGraph` with those carriers, executes
    the named runbook via the local executor, and returns a mapping
    from output role to the corresponding evidence node payloads.

    Loaders and boot-time helpers MUST NOT call this function; they are
    restricted to structural/schema checks only (Option C).
    """
    from .runtime import get_computer

    computer = get_computer(require_runtime_viability=True)
    rb_map = computer.runbooks.by_name.get(runbook_name) or {}
    if not rb_map:
        raise LawValidationError(
            f"no persisted runbook found with name {runbook_name!r} for law enforcement"
        )
    runbook_id = sorted(rb_map.keys())[0]
    runbook = rb_map[runbook_id]

    graph = LocalGraph()
    bindings_in: Dict[str, str] = {}
    for role, payload in inputs.items():
        # Seed the temporary graph without re-enforcing node-level laws;
        # the carriers are already validated persisted objects, and the
        # law runbook itself is the gate we are exercising here.
        node = dict(payload)
        node_id = node["id"]
        existing = graph.nodes.get(node_id)
        if existing is not None and existing != node:
            raise LawValidationError(
                f"law runbook {runbook_name!r} sees conflicting payloads for node {node_id!r}"
            )
        graph.nodes[node_id] = node
        bindings_in[role] = node_id

    bindings_out = execute_runbook_local(
        graph,
        runbook,
        initial_bindings=bindings_in,
    )
    outputs: Dict[str, dict] = {}
    for role, node_id in bindings_out.items():
        node = graph.nodes.get(node_id)
        if node is None:
            raise LawValidationError(
                f"law runbook {runbook_name!r} produced binding for role {role!r} "
                f"referencing unknown node {node_id!r}"
            )
        outputs[role] = node
    return outputs


def check_flow_map_laws(graph: object, flow_map: Mapping[str, object]) -> None:
    """
    Enforce flow laws for a ``flow_map`` carrier using flow_laws_check.

    Raises LawValidationError if:
    - carrier_id is missing or the carrier is absent in graph.nodes,
    - the diagnostic evidence reports status != \"pass\".
    """
    if flow_map.get("kind") != "flow_map":
        return
    carrier_id = flow_map.get("carrier_id")
    if not isinstance(carrier_id, str):
        raise LawValidationError("flow_map must declare carrier_id to check flow laws")
    carrier = getattr(graph, "nodes", {}).get(carrier_id)
    if carrier is None:
        raise LawValidationError(f"flow_map carrier {carrier_id} not present in graph")
    outputs = execute_law_runbook(
        "flow_laws_check",
        inputs={
            "flow_map": dict(flow_map),
            # The carrier is present in the graph passed to the realizer
            # even though it is not a runbook input.
            "carrier": dict(carrier),
        },
    )
    evidence = outputs.get("flow_laws_evidence")
    if evidence is None:
        raise LawValidationError("flow_laws_check runbook did not bind flow_laws_evidence")
    validate_object(evidence)
    if evidence.get("status") != "pass":
        suffix = _summarize_counterexample(evidence)
        raise LawValidationError(f"flow_map {flow_map.get('id')} violates flow laws{suffix}")


def check_nucleus_map_laws(graph: object, nucleus_map: Mapping[str, object]) -> None:
    """
    Enforce nucleus laws for a ``nucleus_map`` carrier using nucleus_laws_check.
    """
    if nucleus_map.get("kind") != "nucleus_map":
        return
    carrier_id = nucleus_map.get("carrier_id")
    if not isinstance(carrier_id, str):
        raise LawValidationError("nucleus_map must declare carrier_id to check nucleus laws")
    carrier = getattr(graph, "nodes", {}).get(carrier_id)
    if carrier is None:
        raise LawValidationError(f"nucleus_map carrier {carrier_id} not present in graph")
    outputs = execute_law_runbook(
        "nucleus_laws_check",
        inputs={
            "nucleus_map": dict(nucleus_map),
            "carrier": dict(carrier),
        },
    )
    evidence = outputs.get("nucleus_laws_evidence")
    if evidence is None:
        raise LawValidationError("nucleus_laws_check runbook did not bind nucleus_laws_evidence")
    validate_object(evidence)
    if evidence.get("status") != "pass":
        suffix = _summarize_counterexample(evidence)
        raise LawValidationError(f"nucleus_map {nucleus_map.get('id')} violates nucleus laws{suffix}")

    # When an observation_equivalence carrier exists whose observation_ids
    # cover the nucleus_map.elements, require the nucleus_table to coincide
    # with the equivalence_table on that domain. This realizes the Nucleate
    # act concretely: the nucleus is the closure induced by the normalized
    # observation equivalence.
    nodes = getattr(graph, "nodes", {})
    elements = set(nucleus_map.get("elements") or [])
    if elements:
        candidates: list[Mapping[str, object]] = []
        for node in nodes.values():
            if node.get("kind") != "observation_equivalence":
                continue
            obs_ids = set(node.get("observation_ids") or [])
            if elements.issubset(obs_ids):
                candidates.append(node)
        if len(candidates) > 1:
            raise LawValidationError(
                "multiple observation_equivalence carriers cover the nucleus_map elements; "
                "Nucleate closure would be ambiguous"
            )
        if candidates:
            eq = candidates[0]
            eq_table = eq.get("equivalence_table") or {}
            nucleus_table = nucleus_map.get("nucleus_table") or {}
            missing = [e for e in elements if e not in eq_table]
            if missing:
                raise LawValidationError(
                    "observation_equivalence.equivalence_table must contain all nucleus_map elements "
                    f"when it covers them; missing: {sorted(missing)}"
                )
            mismatches = [
                e for e in elements if nucleus_table.get(e) != eq_table.get(e)
            ]
            if mismatches:
                raise LawValidationError(
                    "nucleus_map.nucleus_table must coincide with observation_equivalence.equivalence_table "
                    f"on its elements; mismatches at {sorted(mismatches)}"
                )


def check_system_laws(objects_by_id: Mapping[str, dict], system: Mapping[str, object]) -> None:
    """
    Enforce system-level laws for a ``system`` carrier using system_laws_check.

    This is object-index oriented and does not mutate any graph; it is
    intended for loader-time and API-level checks.
    """
    if system.get("kind") != "system":
        return

    def _require(obj_id: str, kind: str) -> dict:
        obj = objects_by_id.get(obj_id)
        if obj is None:
            raise LawValidationError(f"system references missing {kind} object {obj_id}")
        if obj.get("kind") != kind:
            raise LawValidationError(
                f"system reference {obj_id} expected kind {kind} but found {obj.get('kind')}"
            )
        return obj

    profile = _require(system["profile_topos_id"], "profile_topos")
    phase_space = _require(system["phase_space_id"], "phase_space")
    measurement_frame = _require(system["measurement_frame_id"], "measurement_frame")
    regime = _require(system["regime_id"], "regime")
    trace = _require(system["trace_id"], "trace")
    fixed_invariants = _require(system["fixed_invariants_id"], "fixed_invariants")
    flow_map = _require(system["flow_map_id"], "flow_map")
    nucleus_map = _require(system["nucleus_map_id"], "nucleus_map")

    # Phase space must live on the same lattice as the profile.
    phase_states = set(phase_space.get("states", []))
    profile_elements = set(profile.get("elements", []))
    if phase_states != profile_elements:
        raise LawValidationError("phase_space.states must equal profile_topos.elements in a System")
    # Current state must be an element of the fixed invariants lattice.
    current_state = phase_space.get("current_state")
    if current_state not in set(fixed_invariants.get("elements", [])):
        raise LawValidationError("phase_space.current_state must be a fixed invariant element for the System")
    # Flow/nucleus maps must be defined on the profile lattice.
    if flow_map.get("carrier_id") != profile["id"]:
        raise LawValidationError("system flow_map must have carrier_id equal to profile_topos.id")
    if nucleus_map.get("carrier_id") != profile["id"]:
        raise LawValidationError("system nucleus_map must have carrier_id equal to profile_topos.id")
    if set(flow_map.get("elements", [])) != profile_elements:
        raise LawValidationError("system flow_map elements must equal profile_topos elements")
    if set(nucleus_map.get("elements", [])) != profile_elements:
        raise LawValidationError("system nucleus_map elements must equal profile_topos elements")

    # If the measurement frame declares a term_id, require that it reference a
    # term on the System trace; an optional judgment_id must reference a
    # judgment for that term.
    constraints = measurement_frame.get("constraints") or {}
    term_id = constraints.get("term_id")
    if term_id is not None:
        term = objects_by_id.get(term_id)
        if term is None or term.get("kind") != "term":
            raise LawValidationError("measurement_frame.constraints.term_id must reference a term object")
        if term.get("trace_id") != trace["id"]:
            raise LawValidationError("measurement_frame term_id must reference a term on the System trace")
        judgment_id = constraints.get("judgment_id")
        if judgment_id is not None:
            judgment = objects_by_id.get(judgment_id)
            if judgment is None or judgment.get("kind") != "judgment":
                raise LawValidationError("measurement_frame.constraints.judgment_id must reference a judgment object")
            if judgment.get("term_id") != term_id:
                raise LawValidationError("measurement_frame judgment_id must reference a judgment for the declared term_id")

    # observation_equivalence is not stored directly on the system carrier,
    # but system_laws_check expects one. In a multi-System AOG there may be
    # many observation_equivalence carriers; for each System we must choose
    # one whose observation_ids cover that System's admissible observations.
    admissible = set(measurement_frame.get("admissible_observations") or [])
    if admissible and not admissible.issubset(profile_elements):
        raise LawValidationError("measurement_frame.admissible_observations must be profile_topos elements")
    obs_equivs = [obj for obj in objects_by_id.values() if obj.get("kind") == "observation_equivalence"]
    if not obs_equivs:
        raise LawValidationError("system_laws_check requires at least one observation_equivalence object")
    if not admissible:
        # When the measurement frame does not declare any admissible
        # observations, coverage is vacuous; select a deterministically
        # minimal observation_equivalence by id so that the resulting graph
        # is independent of dictionary iteration order.
        observation_equivalence = min(obs_equivs, key=lambda obj: obj["id"])
    else:
        candidates = []
        for eq in obs_equivs:
            obs_ids = set(eq.get("observation_ids") or [])
            if admissible.issubset(obs_ids):
                candidates.append(eq)
        if not candidates:
            raise LawValidationError(
                "system_laws_check requires an observation_equivalence whose "
                "observation_ids cover all measurement_frame.admissible_observations"
            )
        observation_equivalence = min(candidates, key=lambda obj: obj["id"])

    class _GraphView:
        def __init__(self, nodes: Mapping[str, dict]) -> None:
            self.nodes: Dict[str, dict] = dict(nodes)
            self.edges: Dict[str, object] = {}

    graph_view = _GraphView(objects_by_id)
    from .realizers.system_laws_check import realize as system_laws_realizer

    output = system_laws_realizer(
        graph_view,
        inputs={
            "system": dict(system),
            "profile_topos": dict(profile),
            "phase_space": dict(phase_space),
            "measurement_frame": dict(measurement_frame),
            "regime": dict(regime),
            "trace": dict(trace),
            "fixed_invariants": dict(fixed_invariants),
            "flow_map": dict(flow_map),
            "nucleus_map": dict(nucleus_map),
            "observation_equivalence": dict(observation_equivalence),
        },
        context={"runbook": {"id": "0" * 64, "name": "system_laws_check"}, "step": {"step_index": 0}},
    )
    if not output.nodes:
        raise LawValidationError("system_laws_check did not emit evidence node")
    evidence = output.nodes[0]
    validate_object(evidence)
    if evidence.get("status") != "pass":
        suffix = _summarize_counterexample(evidence)
        raise LawValidationError(f"system {system.get('id')} violates system laws{suffix}")


def check_reducibility_candidates_laws(objects_by_id: Mapping[str, dict], candidates: Mapping[str, object]) -> None:
    """
    Enforce reducibility candidate laws.

    Per the README, reducibility candidates must:
    - be total on the variables of their term_context; and
    - cite typing and normalization evidence (JudgeTyping / NormalizeStrongly).

    In this machine, typing evidence is carried by ``judgment`` carriers and
    normalization evidence by ``syntax_normal_form`` carriers.
    """
    if candidates.get("kind") != "reducibility_candidates":
        return

    context_id = candidates.get("context_id")
    context = objects_by_id.get(str(context_id))
    if context is None or context.get("kind") != "term_context":
        raise LawValidationError(
            f"reducibility_candidates.context_id {context_id!r} must reference a term_context object"
        )
    vars_ctx = list(context.get("variables", []))
    cand_map: Mapping[str, dict] = candidates.get("candidates") or {}

    # Totality: every context variable must appear in the candidate map.
    missing = [v for v in vars_ctx if v not in cand_map]
    if missing:
        raise LawValidationError(
            f"reducibility_candidates missing entries for context variables {sorted(missing)}"
        )

    # Evidence checks for each candidate.
    for var in vars_ctx:
        entry = cand_map.get(var) or {}
        term_id = entry.get("term_id")
        typing_id = entry.get("typing_witness_id")
        norm_id = entry.get("normalization_witness_id")
        term = objects_by_id.get(str(term_id))
        if term is None or term.get("kind") != "term":
            raise LawValidationError(
                f"reducibility candidate {var!r} must reference a term carrier via term_id"
            )
        judgment = objects_by_id.get(str(typing_id))
        if judgment is None or judgment.get("kind") != "judgment" or judgment.get("term_id") != term_id:
            raise LawValidationError(
                f"reducibility candidate {var!r} typing_witness_id must reference a judgment for term {term_id}"
            )
        syntax_nf = objects_by_id.get(str(norm_id))
        if syntax_nf is None or syntax_nf.get("kind") != "syntax_normal_form" or syntax_nf.get("term_id") != term_id:
            raise LawValidationError(
                f"reducibility candidate {var!r} normalization_witness_id must reference a syntax_normal_form for term {term_id}"
            )


def check_runbook_laws(runbook: Mapping[str, object], regime: Mapping[str, object] | None = None) -> None:
    """
    Enforce runbook-level laws for a persisted runbook using runbook_laws_check.

    The regime, when provided, is used to enforce suppression constraints
    for the system_interaction runbook.
    """
    name = runbook.get("name")
    if not isinstance(name, str):
        raise LawValidationError("runbook must provide a string 'name' to check runbook laws")
    # Law-check infrastructure runbooks are trusted by construction.
    if name in {"runbook_laws_check"}:
        return

    inputs: Dict[str, dict] = {}
    if regime is not None:
        if regime.get("kind") != "regime":
            raise LawValidationError("regime used for runbook_laws_check must have kind 'regime'")
        inputs["regime"] = dict(regime)
    # The runbook_laws_check realizer expects the runbook under test in the
    # context rather than as a graph node. We therefore continue to invoke
    # it directly here, while other law checks (flow/system/nucleus) are
    # routed through their dedicated runbooks.
    from .realizers.runbook_laws_check import realize as runbook_laws_realizer

    output = runbook_laws_realizer(
        graph=None,
        inputs=inputs,
        context={"runbook": dict(runbook), "step": {"step_index": 0}},
    )
    if not output.nodes:
        raise LawValidationError("runbook_laws_check did not emit evidence node")
    evidence = output.nodes[0]
    validate_object(evidence)
    if evidence.get("status") != "pass":
        suffix = _summarize_counterexample(evidence)
        raise LawValidationError(f"runbook {runbook.get('id')} ({name}) violates runbook laws{suffix}")


def check_geometry_profile_laws(graph: object, geometry: Mapping[str, object]) -> None:
    """
    Enforce laws for a ``geometry_profile`` carrier.

    GeometryProfile = (FlowProfile NucleateProfile) packages a commuting flow/nucleus
    pair on the profile lattice. The carrier must therefore reference:
    - a profile_topos lattice,
    - a flow_map and nucleus_map on that lattice,
    - flow_laws_evidence and nucleus_laws_evidence certifying the lattice laws, and
    - commutation_evidence certifying F∘ν = ν∘F on the same lattice.
    """
    if geometry.get("kind") != "geometry_profile":
        return

    nodes: Dict[str, dict] = getattr(graph, "nodes", {})

    def _require(obj_id: str, kind: str) -> dict:
        obj = nodes.get(obj_id)
        if obj is None:
            raise LawValidationError(f"geometry_profile references missing {kind} object {obj_id}")
        if obj.get("kind") != kind:
            raise LawValidationError(
                f"geometry_profile reference {obj_id} expected kind {kind} but found {obj.get('kind')}"
            )
        return obj

    profile = _require(str(geometry["profile_topos_id"]), "profile_topos")
    flow_map = _require(str(geometry["flow_map_id"]), "flow_map")
    nucleus_map = _require(str(geometry["nucleus_map_id"]), "nucleus_map")
    flow_ev = _require(str(geometry["flow_laws_evidence_id"]), "flow_laws_evidence")
    nucleus_ev = _require(str(geometry["nucleus_laws_evidence_id"]), "nucleus_laws_evidence")
    comm_ev = _require(str(geometry["commutation_evidence_id"]), "commutation_evidence")

    # Carrier alignment: flow/nucleus maps must share the profile carrier and
    # elements; evidence carriers must reference the same IDs.
    profile_id = profile["id"]
    flow_carrier = flow_map.get("carrier_id")
    nuc_carrier = nucleus_map.get("carrier_id")
    if flow_carrier != profile_id or nuc_carrier != profile_id:
        raise LawValidationError("geometry_profile flow_map/nucleus_map must use profile_topos as carrier")
    elements = set(profile.get("elements", []))
    flow_elements = set(flow_map.get("elements", []))
    nucleus_elements = set(nucleus_map.get("elements", []))
    if elements != flow_elements or elements != nucleus_elements:
        raise LawValidationError("geometry_profile flow_map/nucleus_map elements must equal profile_topos elements")

    # Flow laws evidence must certify the flow on the profile lattice.
    if flow_ev.get("status") != "pass":
        raise LawValidationError("geometry_profile requires flow_laws_evidence.status == 'pass'")
    if flow_ev.get("flow_id") != flow_map["id"] or flow_ev.get("carrier_id") != profile_id:
        raise LawValidationError("geometry_profile flow_laws_evidence must reference the profile flow_map and carrier")

    # Nucleus laws evidence must certify the nucleus on the profile lattice.
    if nucleus_ev.get("status") != "pass":
        raise LawValidationError("geometry_profile requires nucleus_laws_evidence.status == 'pass'")
    if nucleus_ev.get("nucleus_id") != nucleus_map["id"] or nucleus_ev.get("carrier_id") != profile_id:
        raise LawValidationError(
            "geometry_profile nucleus_laws_evidence must reference the profile nucleus_map and carrier"
        )

    # Commutation evidence must certify F∘ν = ν∘F on the same lattice.
    if comm_ev.get("status") != "pass":
        raise LawValidationError("geometry_profile requires commutation_evidence.status == 'pass'")
    if (
        comm_ev.get("flow_id") != flow_map["id"]
        or comm_ev.get("nucleus_id") != nucleus_map["id"]
        or comm_ev.get("carrier_id") != profile_id
    ):
        raise LawValidationError(
            "geometry_profile commutation_evidence must reference the profile flow_map, nucleus_map, and carrier"
        )
    table = comm_ev.get("table") or []
    if {row.get("element") for row in table} != elements:
        raise LawValidationError(
            "geometry_profile commutation_evidence.table must cover exactly the profile_topos elements"
        )


def enforce_object_index_laws(objects_by_id: Mapping[str, dict]) -> None:
    """
    Apply optional law diagnostics across an in-memory object index.

    This is a *post-boot* tool: it may be used by tests or diagnostic
    scripts to run Flow/Nucleus/geometry gates against persisted
    carriers, but MUST NOT be invoked from the structural loaders or
    boot-time viability checks.
    """

    class _GraphView:
        def __init__(self, nodes: Mapping[str, dict]) -> None:
            self.nodes: Dict[str, dict] = dict(nodes)
            self.edges: Dict[str, object] = {}

    graph_view = _GraphView(objects_by_id)

    for obj in objects_by_id.values():
        kind = obj.get("kind")
        if kind == "flow_map":
            check_flow_map_laws(graph_view, obj)
        elif kind == "nucleus_map":
            check_nucleus_map_laws(graph_view, obj)
        elif kind == "geometry_profile":
            check_geometry_profile_laws(graph_view, obj)
        elif kind == "reducibility_candidates":
            check_reducibility_candidates_laws(objects_by_id, obj)


def enforce_runbook_index_laws(
    runbooks_by_id: Mapping[str, dict],
    regime: Mapping[str, object] | None,
) -> None:
    """
    Apply runbook law enforcement across an in-memory runbook index.

    The regime, when provided, is usually a System's regime carrier loaded
    from objects, but no particular System is privileged.
    """
    for rb in runbooks_by_id.values():
        check_runbook_laws(rb, regime=regime)


def enforce_node_laws(graph: object, payload: Mapping[str, object]) -> None:
    """
    Entry point used by RelationalGraph.add_node.

    It reuses the same flow/nucleus/geometry gates but against the live
    graph instance rather than an object index.
    """
    kind = payload.get("kind")
    if kind == "flow_map":
        check_flow_map_laws(graph, payload)
    elif kind == "nucleus_map":
        check_nucleus_map_laws(graph, payload)
    elif kind == "geometry_profile":
        check_geometry_profile_laws(graph, payload)


def validate_raw_object(payload: MutableMapping[str, object]) -> None:
    """
    Full law-enforcement pipeline for a raw, external carrier payload.

    This is intended for API- and service-level entrypoints that accept
    objects which are not yet part of the persisted object index.

    Pipeline:
    - canonicalize and assign ``id`` via ``ensure_id_coherence``;
    - validate against the JSON schema and carrier-level laws via
      :func:`validate_object`.

    Graph-level laws (flow/nucleus/geometry) are enforced when the
    payload is inserted into a graph-like view via
    :func:`enforce_node_laws`.
    """
    ensure_id_coherence(payload)
    validate_object(payload)


def validate_raw_runbook(payload: MutableMapping[str, object]) -> None:
    """
    Full structural validation pipeline for a raw runbook payload.

    This performs:
    - canonicalization and ``id`` assignment via ``ensure_id_coherence``;
    - schema/typing validation via :func:`validate_runbook`.

    Operator→realizer coverage is *not* checked here; that is a runtime
    concern handled by :func:`validate_realizer_coverage` during boot.
    """
    from .validation import validate_runbook

    ensure_id_coherence(payload)
    validate_runbook(payload)


def validate_realizer_coverage(
    objects_by_id: Mapping[str, dict],
    runbooks_by_id: Mapping[str, dict],
) -> None:
    """
    Validate that realizers cover the declared operator surface.

    This is a *computing-surface* check rather than a pure graph law:
    it ensures that the declared runbook/operator vocabulary can in fact
    be realized by Python modules.

    Checks (runtime viability):
    - every operator declared in the runbook schema has a resolvable
      realizer module;
    - every persisted runbook's name and step operators are drawn from
      the schema enums (no ad-hoc or undeclared operators).

    This complements :func:`check_runbook_laws`, which focuses on typing
    and sequencing within a single runbook, and the index-level law
    enforcement performed by :func:`enforce_runbook_index_laws`.
    """
    schema = load_schema("runbook.schema.yaml")
    operator_enum = set(
        schema["properties"]["steps"]["items"]["properties"]["operator"]["enum"]
    )
    name_enum = set(schema["properties"]["name"]["enum"])

    # Every declared operator must correspond to a realizer module.
    for op in sorted(operator_enum):
        try:
            resolve_realizer(op)
        except ImportError as exc:  # pragma: no cover - defensive
            raise LawValidationError(
                f"runbook schema declares operator {op!r} without a resolvable realizer"
            ) from exc

    # Persisted runbooks must use only declared operators; step ``name`` is
    # descriptive metadata and is not constrained beyond the usual typing
    # checks enforced by runbook_laws_check.
    for rb in runbooks_by_id.values():
        name = rb.get("name")
        if not isinstance(name, str) or name not in name_enum:
            raise LawValidationError(
                f"runbook {rb.get('id')} has name {name!r} not declared in runbook schema"
            )
        for step in rb.get("steps", []):
            op = step.get("operator")
            if op not in operator_enum:
                raise LawValidationError(
                    f"runbook {name!r} step {step.get('step_index')} "
                    f"uses operator {op!r} not declared in runbook schema"
                )
