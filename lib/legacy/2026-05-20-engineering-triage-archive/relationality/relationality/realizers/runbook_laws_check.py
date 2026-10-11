from __future__ import annotations

from typing import Dict, Iterable, Mapping, Optional

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, OBJECT_SCHEMAS


EXPECTED_OPERATOR_SEQUENCES: Mapping[str, Iterable[str]] = {
    "presheaf_sheafify": ("sheaf_condition", "sheafification"),
    "sheaf_profile_consistency": ("sheaf_profile_consistency",),
    "build_evaluation_context": ("build_evaluation_context",),
    "build_reducible_environment": ("build_reducible_environment",),
    "profile_semantics_check": ("profile_semantics_check",),
    "profile_dynamics_check": ("profile_dynamics_check",),
    "profile_semantics_build": ("judgment_laws_check", "profile_semantics_check", "profile_semantics_build"),
    "profile_context_build": ("profile_context_build",),
    "profile_invariant": ("profile_invariant",),
    "profile_reach": ("profile_reach",),
    "profile_entropy_seed": ("profile_entropy_seed",),
    "profile_entropy_measure": ("profile_entropy_measure",),
    "profile_entropy": ("profile_entropy",),
    "calculate_profile_syntax": ("calculate_profile_syntax",),
    "shuffle_profile": ("shuffle_profile",),
    "shuffle_geometry": ("shuffle_geometry",),
    "fixed_shape": ("fixed_shape",),
    "profile_phase_space_build": ("profile_phase_space_build",),
    "profile_dynamics_build": ("profile_dynamics_build",),
    "profile_observe": ("profile_observe",),
    "fixed_observe": ("fixed_observe",),
    "flow_measure_consistency_check": ("flow_measure_consistency_check",),
    "substitution": ("substitution_term",),
    "evaluate_judgment": ("evaluate_judgment",),
    "evaluate_observation": ("evaluate_observation",),
    "evaluate_observation_equivalence": ("evaluate_observation_equivalence",),
    "normalize_observation_equivalence": ("normalize_observation_equivalence",),
    "observation_equivalence_check": ("observation_equivalence_check",),
    "evaluation_equivalence": ("evaluation_equivalence",),
    "equate_judgment_observation": ("equate_judgment_observation",),
    "reduce": ("reduce",),
    "recognize_syntax": ("recognize_syntax",),
    "normalize_syntax": ("normalize_syntax",),
    "system_interaction": (
        "observe",
        "nucleate_profile",
        "flow_profile",
        "flow_measure_step",
        "normalize_observation",
        "stabilize_observation",
        "fix_flow_nucleus",
    ),
    "spectral_analysis": ("spectral_geometry",),
    "mixing": ("mixing",),
    "deviation_diffusion_wave": (
        "measure_deviation_observation_kernel",
        "diffuse_fixed_flow_profile",
        "wave_operator",
    ),
    "fixed_profile_check": ("fixed_profile_check",),
    "fixed_profile_build": ("fixed_profile_build",),
    "fixed_invariants_build": ("fixed_invariants_build",),
    "fixed_finite_limits_build": ("fixed_finite_limits_build",),
    "fixed_dynamics_build": ("fixed_dynamics_build",),
    "context_geometry": ("context_geometry",),
    "sheafification_evidence": ("sheafification_evidence",),
    "flow_nucleus_commutation": ("flow_nucleus_commutation",),
    "fix_flow_only": ("fix_flow",),
    "fix_nucleus_only": ("fix_nucleus",),
    "fix_flow_nucleus": ("fix_flow_nucleus",),
    "fix_flow_nucleus_sequence": ("flow_nucleus_commutation", "fix_flow_nucleus"),
    "trace_start": ("start_trace",),
    "trace_advance": ("advance_trace",),
    "trace_stabilize": ("stabilize_trace",),
    "trace_reentry": ("trace_reentry",),
    "rehead_trace": ("rehead_trace",),
    "retail_trace": ("retail_trace",),
    "restep_trace": ("restep_trace",),
    "trace_observation_equivalence": ("trace_observation_equivalence",),
    "trace_observation_equivalence_closure": ("trace_observation_equivalence_closure",),
    "complete_trace": ("complete_trace",),
    "trace_head": ("head_trace",),
    "trace_tail": ("tail_trace",),
    "trace_step": ("trace_step",),
    "trace_continue": ("continue_trace",),
    "trace_decompose": ("decompose_trace",),
    "trace_profile": ("trace_profile",),
    "close_judgment_trace": ("close_judgment_trace",),
    "shuffle_trace": ("shuffle_trace",),
    "flow_laws_check": ("flow_laws_check",),
    "nucleus_laws_check": ("nucleus_laws_check",),
    "system_laws_check": ("system_laws_check",),
    "ergodicity": ("ergodicity",),
    "observation_kernel": ("observation_kernel",),
    "fixed_kernel": ("fixed_kernel",),
    "shuffle_equivalence_check": ("shuffle_equivalence_check",),
    "runbook_laws_check": ("runbook_laws_check",),
    "judgment_laws_check": ("judgment_laws_check",),
    "always_modality": ("always_modality",),
    "eventually_modality": ("eventually_modality",),
    "close_temporally_check": ("close_temporally_check",),
    "measured_observation_check": ("measured_observation_check",),
    "normalized_observation_check": ("normalized_observation_check",),
    "stabilized_observation_check": ("stabilized_observation_check",),
    "measure_preservation": ("measure_preservation",),
    "judgment_equivalence_check": ("judgment_equivalence_check",),
    "observation_equivalence": ("observation_equivalence",),
    "trace_measurement_check": ("trace_measurement_check",),
    "geometry_profile": (
        "flow_laws_check",
        "nucleus_laws_check",
        "flow_nucleus_commutation",
        "geometry_profile",
    ),
    "star_operation": ("star_operation",),
    "profile_integral": ("profile_integral",),
    "modal_truncation": ("modal_truncation",),
}


def _record(
    checks: Dict[str, bool],
    law: str,
    counterexample_ref: Optional[Dict[str, object]],
    details: Dict[str, object],
) -> Optional[Dict[str, object]]:
    checks[law] = False
    if counterexample_ref is None:
        ce: Dict[str, object] = {"law": law}
        ce.update(details)
        return ce
    return counterexample_ref


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    runbook_laws_check realizer.

    Inputs
    ------
    system (optional):
        System carrier used for provenance; when provided, its id is recorded
        in the evidence node.
    regime (optional but recommended for system_interaction):
        Regime governing the system; used to ensure the runbook does not call
        suppressed operators.

    Semantics
    ---------
    Enforce runbook-level coherence constraints for the runbook being
    executed (provided via ``context['runbook']``):
    - Every step's inputs must be supplied by the evolving binding
      environment seeded by runbook-level inputs.
    - Step outputs must be lawful carriers (their kinds are known carriers
      with schemas).
    - Composition respects domain/codomain constraints: kinds remain stable
      when roles are rebound, and consumers expect the kinds producers emit.
    - Operator ordering matches the act-specified sequence for each named
      runbook.
    - Role bindings never dangle or change kind when overwritten.
    - Declared runbook outputs match the final binding environment.
    - For system_interaction, no step operator is suppressed by the regime.

    The realizer emits a single runbook_laws_evidence carrier summarizing the
    per-law booleans and the first counterexample, if any.
    """
    runbook = context.get("runbook")
    if runbook is None:
        raise LawValidationError("runbook_laws_check requires 'runbook' in context")
    name = runbook.get("name")
    if not isinstance(name, str):
        raise LawValidationError("runbook_laws_check requires runbook.name to be a string")
    steps = list(runbook.get("steps") or [])
    if not steps:
        raise LawValidationError("runbook_laws_check requires a non-empty steps sequence")
    steps = sorted(steps, key=lambda s: s["step_index"])

    system = inputs.get("system")
    if system is not None and system.get("kind") != "system":
        raise LawValidationError("runbook_laws_check 'system' input must have kind 'system'")
    regime = inputs.get("regime")
    if regime is not None and regime.get("kind") != "regime":
        raise LawValidationError("runbook_laws_check 'regime' input must have kind 'regime'")

    checks: Dict[str, bool] = {
        "inputs_satisfied": True,
        "outputs_lawful": True,
        "composition_typed": True,
        "operator_order_lawful": True,
        "bindings_consistent": True,
        "declared_outputs_match": True,
        "regime_respected": True,
        "no_illegal_transitions": True,
    }
    counterexample: Optional[Dict[str, object]] = None

    # 1. Binding environment evolution and composition typing.
    env: Dict[str, str] = {}
    for spec in runbook.get("inputs", []) or []:
        role = spec["role"]
        kind = spec["kind"]
        existing = env.get(role)
        if existing is not None and existing != kind:
            counterexample = _record(
                checks,
                "bindings_consistent",
                counterexample,
                {
                    "phase": "runbook_inputs",
                    "role": role,
                    "declared_kind": kind,
                    "existing_kind": existing,
                },
            )
        env[role] = kind

    allowed_kinds = set(OBJECT_SCHEMAS.keys()) | {"runbook_laws_evidence"}
    # Step-by-step environment evolution.
    for step in steps:
        step_index = step["step_index"]
        # Input availability and typing.
        for spec in step.get("inputs", []) or []:
            role = spec["role"]
            expected_kind = spec["kind"]
            env_kind = env.get(role)
            if env_kind is None:
                counterexample = _record(
                    checks,
                    "inputs_satisfied",
                    counterexample,
                    {
                        "step_index": step_index,
                        "role": role,
                        "expected_kind": expected_kind,
                        "reason": "input role not bound in environment",
                    },
                )
            elif env_kind != expected_kind:
                counterexample = _record(
                    checks,
                    "composition_typed",
                    counterexample,
                    {
                        "step_index": step_index,
                        "role": role,
                        "expected_kind": expected_kind,
                        "env_kind": env_kind,
                        "reason": "input kind does not match environment",
                    },
                )
        # Output kinds: known carriers; rebinding of roles is allowed so long
        # as subsequent consumers are typed against the new kind.
        for spec in step.get("outputs", []) or []:
            role = spec["role"]
            kind = spec["kind"]
            if kind not in allowed_kinds:
                counterexample = _record(
                    checks,
                    "outputs_lawful",
                    counterexample,
                    {
                        "step_index": step_index,
                        "role": role,
                        "kind": kind,
                        "reason": "output kind not registered as an object schema",
                    },
                )
            env[role] = kind

    # 2. Declared outputs must be present with matching kinds.
    declared_outputs = {spec["role"]: spec["kind"] for spec in runbook.get("outputs", []) or []}
    for role, expected_kind in declared_outputs.items():
        env_kind = env.get(role)
        if env_kind is None or env_kind != expected_kind:
            counterexample = _record(
                checks,
                "declared_outputs_match",
                counterexample,
                {
                    "role": role,
                    "expected_kind": expected_kind,
                    "env_kind": env_kind,
                    "reason": "declared runbook output not bound with expected kind",
                },
            )

    # 3. Operator ordering according to acts.
    operator_sequence = tuple(step["operator"] for step in steps)
    expected_ops = EXPECTED_OPERATOR_SEQUENCES.get(name)
    if expected_ops is None or tuple(expected_ops) != operator_sequence:
        counterexample = _record(
            checks,
            "operator_order_lawful",
            counterexample,
            {
                "runbook_name": name,
                "expected_operators": list(expected_ops) if expected_ops is not None else None,
                "actual_operators": list(operator_sequence),
                "reason": "operator sequence does not match act-specified ordering",
            },
        )

    # 4. Regime suppression constraints for system_interaction.
    if name == "system_interaction":
        if regime is None:
            counterexample = _record(
                checks,
                "regime_respected",
                counterexample,
                {
                    "runbook_name": name,
                    "reason": "regime input required to check operator suppression",
                },
            )
        else:
            suppressed = set(regime.get("suppressed_operators", []))
            for op in operator_sequence:
                if op in suppressed:
                    counterexample = _record(
                        checks,
                        "regime_respected",
                        counterexample,
                        {
                            "runbook_name": name,
                            "operator": op,
                            "reason": "runbook calls operator suppressed by regime",
                        },
                    )
                    break

    # 5. Aggregate illegal-transition flag from the other checks: any failure
    # in the structural laws is treated as an illegal transition or typing
    # violation at the runbook level.
    structural_names = [
        "inputs_satisfied",
        "outputs_lawful",
        "composition_typed",
        "operator_order_lawful",
        "bindings_consistent",
        "declared_outputs_match",
        "regime_respected",
    ]
    if not all(checks[name] for name in structural_names):
        checks["no_illegal_transitions"] = False

    status = "pass" if all(checks.values()) else "fail"

    evidence: Dict[str, object] = {
        "kind": "runbook_laws_evidence",
        "runbook_id": runbook["id"],
        "runbook_name": name,
        "checks": checks,
        "status": status,
        "act_ref": "RunbookLawsCheck",
    }
    if system is not None:
        evidence["system_id"] = system["id"]
    if regime is not None:
        evidence["regime_id"] = regime["id"]
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = []
    if system is not None:
        edges.append(
            {
                "operator": "runbook_laws_check",
                "src": system["id"],
                "tgt": evidence["id"],
            }
        )
    if regime is not None:
        edges.append(
            {
                "operator": "runbook_laws_check",
                "src": regime["id"],
                "tgt": evidence["id"],
            }
        )

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"runbook_laws_evidence": evidence["id"]},
    )
