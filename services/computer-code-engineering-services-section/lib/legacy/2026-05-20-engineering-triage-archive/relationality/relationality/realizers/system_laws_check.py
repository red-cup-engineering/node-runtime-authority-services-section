from __future__ import annotations

from typing import Dict, Iterable, Tuple

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def _record(
    checks: Dict[str, bool],
    law: str,
    counterexample_ref: Dict[str, object] | None,
    details: Dict[str, object],
) -> Dict[str, object] | None:
    checks[law] = False
    if counterexample_ref is None:
        ce: Dict[str, object] = {"law": law}
        ce.update(details)
        return ce
    return counterexample_ref


def _table_equal_on_subset(table_a: dict, table_b: dict, subset: Iterable[str]) -> bool:
    for x in subset:
        row_a = table_a.get(x, {})
        row_b = table_b.get(x, {})
        for y in subset:
            if row_a.get(y) != row_b.get(y):
                return False
    return True


def _order_equal_on_subset(order_a: dict, order_b: dict, subset: Iterable[str]) -> bool:
    for x in subset:
        row_a = order_a.get(x, [])
        row_b = order_b.get(x, [])
        if set(row_a) != set(row_b):
            return False
    return True


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    system_laws_check realizer.

    Inputs
    ------
    system:
        System carrier naming the constituent nodes of the System.
    profile_topos, phase_space, measurement_frame, regime, trace,
    fixed_invariants, flow_map, nucleus_map, observation_equivalence:
        Carriers referenced by the System and its dynamics.

    Semantics
    ---------
    Enforce global coherence conditions at the System level:
    - ProfileTopos / PhaseSpace / FixedInvariants lattice alignment.
    - FlowMap and NucleusMap carrier alignment.
    - FixedInvariants correctness as fixed points of flow and nucleus.
    - MeasurementFrame admissibility against the profile lattice.
    - ObservationEquivalence coverage for all admissible observations.
    - Trace carrier alignment with PhaseSpace.
    - Regime operator completeness for system_interaction.

    The realizer emits a single system_laws_evidence carrier summarizing the
    per-law booleans and the first counterexample, if any. Structural
    inconsistencies are reported via evidence rather than raised, reserving
    LawValidationError for gross kind/shape mismatches.
    """
    system = inputs.get("system")
    profile = inputs.get("profile_topos")
    phase_space = inputs.get("phase_space")
    measurement_frame = inputs.get("measurement_frame")
    regime = inputs.get("regime")
    trace = inputs.get("trace")
    fixed_invariants = inputs.get("fixed_invariants")
    flow_map = inputs.get("flow_map")
    nucleus_map = inputs.get("nucleus_map")
    observation_equivalence = inputs.get("observation_equivalence")

    if system is None:
        raise KeyError("system_laws_check requires 'system' input")
    if profile is None or phase_space is None or measurement_frame is None or regime is None:
        raise KeyError("system_laws_check requires profile_topos, phase_space, measurement_frame, and regime inputs")
    if trace is None or fixed_invariants is None:
        raise KeyError("system_laws_check requires trace and fixed_invariants inputs")
    if flow_map is None or nucleus_map is None:
        raise KeyError("system_laws_check requires flow_map and nucleus_map inputs")
    if observation_equivalence is None:
        raise KeyError("system_laws_check requires observation_equivalence input")

    if system.get("kind") != "system":
        raise LawValidationError("system_laws_check 'system' input must have kind 'system'")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("system_laws_check 'profile_topos' input must have kind 'profile_topos'")
    if phase_space.get("kind") != "phase_space":
        raise LawValidationError("system_laws_check 'phase_space' input must have kind 'phase_space'")
    if measurement_frame.get("kind") != "measurement_frame":
        raise LawValidationError("system_laws_check 'measurement_frame' input must have kind 'measurement_frame'")
    if regime.get("kind") != "regime":
        raise LawValidationError("system_laws_check 'regime' input must have kind 'regime'")
    if trace.get("kind") != "trace":
        raise LawValidationError("system_laws_check 'trace' input must have kind 'trace'")
    if fixed_invariants.get("kind") != "fixed_invariants":
        raise LawValidationError("system_laws_check 'fixed_invariants' input must have kind 'fixed_invariants'")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("system_laws_check 'flow_map' input must have kind 'flow_map'")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("system_laws_check 'nucleus_map' input must have kind 'nucleus_map'")
    if observation_equivalence.get("kind") != "observation_equivalence":
        raise LawValidationError(
            "system_laws_check 'observation_equivalence' input must have kind 'observation_equivalence'"
        )

    checks = {
        "profile_phase_fixed_lattice_alignment": True,
        "flow_nucleus_carrier_alignment": True,
        "fixed_invariants_fixed_points": True,
        "measurement_frame_recognition_alignment": True,
        "observation_equivalence_coverage": True,
        "trace_alignment": True,
        "regime_operator_completeness": True,
    }
    counterexample: Dict[str, object] | None = None

    # 1. ProfileTopos / PhaseSpace / FixedInvariants lattice alignment.
    # System references must match the supplied carriers.
    system_refs_ok = (
        system.get("profile_topos_id") == profile.get("id")
        and system.get("phase_space_id") == phase_space.get("id")
        and system.get("measurement_frame_id") == measurement_frame.get("id")
        and system.get("regime_id") == regime.get("id")
        and system.get("trace_id") == trace.get("id")
        and system.get("fixed_invariants_id") == fixed_invariants.get("id")
    )
    if not system_refs_ok:
        counterexample = _record(
            checks,
            "profile_phase_fixed_lattice_alignment",
            counterexample,
            {
                "reason": "system references do not match supplied carriers",
                "system": {
                    "profile_topos_id": system.get("profile_topos_id"),
                    "phase_space_id": system.get("phase_space_id"),
                    "measurement_frame_id": system.get("measurement_frame_id"),
                    "regime_id": system.get("regime_id"),
                    "trace_id": system.get("trace_id"),
                    "fixed_invariants_id": system.get("fixed_invariants_id"),
                },
            },
        )

    profile_elements = set(profile.get("elements", []))
    phase_states = set(phase_space.get("states", []))
    fixed_elements = set(fixed_invariants.get("elements", []))

    if not phase_states.issubset(profile_elements):
        counterexample = _record(
            checks,
            "profile_phase_fixed_lattice_alignment",
            counterexample,
            {
                "reason": "phase_space.states must be contained in profile_topos.elements",
                "extra_states": sorted(phase_states - profile_elements),
            },
        )
    if not fixed_elements.issubset(profile_elements):
        counterexample = _record(
            checks,
            "profile_phase_fixed_lattice_alignment",
            counterexample,
            {
                "reason": "fixed_invariants.elements must be contained in profile_topos.elements",
                "extra_fixed_elements": sorted(fixed_elements - profile_elements),
            },
        )

    # On the overlapping domains, lattice operations must agree.
    shared_state_elements = phase_states & profile_elements
    if shared_state_elements:
        if phase_space.get("bottom") != profile.get("bottom") or phase_space.get("top") != profile.get("top"):
            counterexample = _record(
                checks,
                "profile_phase_fixed_lattice_alignment",
                counterexample,
                {
                    "reason": "phase_space bottom/top must equal profile_topos bottom/top",
                    "phase_space_bottom": phase_space.get("bottom"),
                    "phase_space_top": phase_space.get("top"),
                    "profile_bottom": profile.get("bottom"),
                    "profile_top": profile.get("top"),
                },
            )
        if not _order_equal_on_subset(profile["order"], phase_space["order"], shared_state_elements):
            counterexample = _record(
                checks,
                "profile_phase_fixed_lattice_alignment",
                counterexample,
                {"reason": "order tables disagree between profile_topos and phase_space on shared states"},
            )
        for table_name in ("meet_table", "join_table", "imply_table"):
            if not _table_equal_on_subset(
                profile[table_name],
                phase_space[table_name],
                shared_state_elements,
            ):
                counterexample = _record(
                    checks,
                    "profile_phase_fixed_lattice_alignment",
                    counterexample,
                    {
                        "reason": f"{table_name} disagrees between profile_topos and phase_space on shared states",
                        "table": table_name,
                    },
                )
                break
        for elt in shared_state_elements:
            if profile["negate_map"].get(elt) != phase_space["negate_map"].get(elt):
                counterexample = _record(
                    checks,
                    "profile_phase_fixed_lattice_alignment",
                    counterexample,
                    {
                        "reason": "negate_map disagrees between profile_topos and phase_space",
                        "element": elt,
                        "profile_neg": profile["negate_map"].get(elt),
                        "phase_space_neg": phase_space["negate_map"].get(elt),
                    },
                )
                break

    shared_fixed_elements = fixed_elements & profile_elements
    if shared_fixed_elements:
        if not _order_equal_on_subset(profile["order"], fixed_invariants["order"], shared_fixed_elements):
            counterexample = _record(
                checks,
                "profile_phase_fixed_lattice_alignment",
                counterexample,
                {
                    "reason": "order tables disagree between profile_topos and fixed_invariants on shared elements",
                    "table": "order",
                },
            )
        for table_name in ("meet_table", "join_table", "imply_table"):
            if not _table_equal_on_subset(
                profile[table_name],
                fixed_invariants[table_name],
                shared_fixed_elements,
            ):
                counterexample = _record(
                    checks,
                    "profile_phase_fixed_lattice_alignment",
                    counterexample,
                    {
                        "reason": f"{table_name} disagrees between profile_topos and fixed_invariants on shared elements",
                        "table": table_name,
                    },
                )
                break
        for elt in shared_fixed_elements:
            if profile["negate_map"].get(elt) != fixed_invariants["negate_map"].get(elt):
                counterexample = _record(
                    checks,
                    "profile_phase_fixed_lattice_alignment",
                    counterexample,
                    {
                        "reason": "negate_map disagrees between profile_topos and fixed_invariants",
                        "element": elt,
                        "profile_neg": profile["negate_map"].get(elt),
                        "fixed_neg": fixed_invariants["negate_map"].get(elt),
                    },
                )
                break

    # 2. FlowMap and NucleusMap carrier alignment.
    flow_carrier_id = flow_map.get("carrier_id")
    nucleus_carrier_id = nucleus_map.get("carrier_id")
    flow_elements = set(flow_map.get("elements", []))
    nucleus_elements = set(nucleus_map.get("elements", []))
    if flow_carrier_id != profile.get("id") or nucleus_carrier_id != profile.get("id"):
        counterexample = _record(
            checks,
            "flow_nucleus_carrier_alignment",
            counterexample,
            {
                "reason": "flow_map and nucleus_map carrier_id must equal profile_topos.id",
                "flow_carrier_id": flow_carrier_id,
                "nucleus_carrier_id": nucleus_carrier_id,
                "profile_topos_id": profile.get("id"),
            },
        )
    if flow_elements != nucleus_elements or flow_elements != profile_elements:
        counterexample = _record(
            checks,
            "flow_nucleus_carrier_alignment",
            counterexample,
            {
                "reason": "flow_map.elements, nucleus_map.elements, and profile_topos.elements must agree",
                "flow_elements": sorted(flow_elements),
                "nucleus_elements": sorted(nucleus_elements),
                "profile_elements": sorted(profile_elements),
            },
        )

    # 3. FixedInvariants correctness: elements are fixed points of flow and nucleus.
    flow_table = flow_map.get("flow_table", {})
    nucleus_table = nucleus_map.get("nucleus_table", {})
    for elt in fixed_elements:
        if elt not in flow_elements or elt not in nucleus_elements:
            counterexample = _record(
                checks,
                "fixed_invariants_fixed_points",
                counterexample,
                {
                    "reason": "fixed_invariants element not in flow/nucleus carrier elements",
                    "element": elt,
                },
            )
            break
        f_elt = flow_table.get(elt)
        n_elt = nucleus_table.get(elt)
        if f_elt != elt or n_elt != elt:
            counterexample = _record(
                checks,
                "fixed_invariants_fixed_points",
                counterexample,
                {
                    "reason": "fixed_invariants element is not jointly fixed by flow and nucleus",
                    "element": elt,
                    "flow_image": f_elt,
                    "nucleus_image": n_elt,
                },
            )
            break

    # 4. MeasurementFrame admissibility coverage over profile recognitions.
    admissible = measurement_frame.get("admissible_observations", [])
    for obs_id in admissible:
        if obs_id not in profile_elements:
            counterexample = _record(
                checks,
                "measurement_frame_recognition_alignment",
                counterexample,
                {
                    "reason": "measurement_frame.admissible_observations must reference profile_topos elements",
                    "observation_id": obs_id,
                },
            )
            break

    # 5. ObservationEquivalence coverage for all admissible observations.
    obs_ids = set(observation_equivalence.get("observation_ids", []))
    admissible_set = set(admissible)
    missing = admissible_set - obs_ids
    if missing:
        counterexample = _record(
            checks,
            "observation_equivalence_coverage",
            counterexample,
            {
                "reason": "observation_equivalence.observation_ids must cover all admissible observations",
                "missing_observation_ids": sorted(missing),
            },
        )

    # 6. Trace carrier alignment with PhaseSpace.
    try:
        validate_trace(trace)
    except LawValidationError as exc:
        counterexample = _record(
            checks,
            "trace_alignment",
            counterexample,
            {
                "reason": "trace fails internal trace laws validation",
                "error": str(exc),
            },
        )
    trace_elements = trace.get("elements", [])
    if any(element not in phase_states for element in trace_elements):
        bad = [e for e in trace_elements if e not in phase_states]
        counterexample = _record(
            checks,
            "trace_alignment",
            counterexample,
            {
                "reason": "trace.elements must be contained in phase_space.states",
                "extra_trace_elements": bad,
            },
        )
    if trace.get("head") != phase_space.get("current_state"):
        counterexample = _record(
            checks,
            "trace_alignment",
            counterexample,
            {
                "reason": "trace.head must equal phase_space.current_state",
                "trace_head": trace.get("head"),
                "phase_space_current_state": phase_space.get("current_state"),
            },
        )

    # 7. Regime operator completeness for system_interaction.
    required_ops = {
        "observe",
        "nucleate_profile",
        "flow_profile",
        "flow_measure_step",
        "normalize_observation",
        "stabilize_observation",
        "fix_flow_nucleus",
    }
    allowed_ops = set(regime.get("allowed_operators", []))
    suppressed_ops = set(regime.get("suppressed_operators", []))
    missing_allowed = sorted(required_ops - allowed_ops)
    suppressed_required = sorted(required_ops & suppressed_ops)
    if missing_allowed or suppressed_required:
        counterexample = _record(
            checks,
            "regime_operator_completeness",
            counterexample,
            {
                "reason": "regime must allow and not suppress all system_interaction operators",
                "missing_allowed": missing_allowed,
                "suppressed_required": suppressed_required,
            },
        )

    status = "pass" if all(checks.values()) else "fail"

    evidence = {
        "kind": "system_laws_evidence",
        "system_id": system["id"],
        "profile_topos_id": profile["id"],
        "phase_space_id": phase_space["id"],
        "measurement_frame_id": measurement_frame["id"],
        "regime_id": regime["id"],
        "trace_id": trace["id"],
        "fixed_invariants_id": fixed_invariants["id"],
        "flow_map_id": flow_map["id"],
        "nucleus_map_id": nucleus_map["id"],
        "observation_equivalence_id": observation_equivalence["id"],
        "checks": checks,
        "status": status,
        "act_ref": "SystemLawsCheck",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge_ids = [
        system["id"],
        profile["id"],
        phase_space["id"],
        measurement_frame["id"],
        regime["id"],
        trace["id"],
        fixed_invariants["id"],
        flow_map["id"],
        nucleus_map["id"],
        observation_equivalence["id"],
    ]
    edges = [
        {
            "operator": "system_laws_check",
            "src": src_id,
            "tgt": evidence["id"],
        }
        for src_id in edge_ids
    ]

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"system_laws_evidence": evidence["id"]},
    )
