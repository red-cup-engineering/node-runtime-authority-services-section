"""
Validation utilities for carriers and runbooks.

This module is deliberately split into two conceptual layers:

- *Schema validation* — structural typing only, via JSON/YAML schemas.
  This is handled by :func:`validate_against_schema` and should be seen
  as the minimal, purely syntactic correctness predicate.

- *Carrier-local law validation* — object-level laws that can be checked
  using only the data inside a single carrier (finite judgment lattices,
  trace recursion, observation equivalence partition coherence, etc.).
  This is layered on top of schema validation by :func:`validate_object`.

Crucially, **graph-level** and **runbook-level** laws—those that depend
on multiple carriers or on the AOG wiring (Flow/Nucleus/System laws,
runbook sequencing laws, geometry_profile, etc.)—live in
``relationality.law_enforcement`` and are enforced via law-check
runbooks. Loaders and boot-time helpers must not call those gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import itertools
from typing import Any, Mapping, MutableMapping

import jsonschema

from .canonical import assert_id_coherence, ensure_id_coherence, hash_canonical_json
from .schemas import load_schema


OBJECT_SCHEMAS: dict[str, str] = {
    "profile_topos": "profile-topos.schema.json",
    "spectral_geometry": "spectral-geometry.schema.json",
    "geometry_profile": "geometry-profile.schema.json",
    "phase_space": "phase-space.schema.json",
    "observation": "observation.schema.json",
    "measurement_frame": "measurement-frame.schema.json",
    "regime": "regime.schema.json",
    "trace": "trace.schema.json",
    "term": "term.schema.json",
    "fixed_invariants": "fixed-invariants.schema.json",
    "observation_carrier": "observation-carrier.schema.json",
    "system": "system.schema.json",
    "flow_map": "flow-map.schema.json",
    "nucleus_map": "nucleus-map.schema.json",
    "entropy_measurement": "entropy-measurement.schema.json",
    "commutation_evidence": "commutation-evidence.schema.json",
    "flow_laws_evidence": "flow-laws-evidence.schema.json",
    "fix_flow_iteration_evidence": "fix-flow-iteration-evidence.schema.json",
    "fix_nucleus_iteration_evidence": "fix-nucleus-iteration-evidence.schema.json",
    "fix_flow_nucleus_iteration_evidence": "fix-flow-nucleus-iteration-evidence.schema.json",
    "observation_kernel": "observation-kernel.schema.json",
    "fixed_kernel": "fixed-kernel.schema.json",
    "mixing_evidence": "mixing-evidence.schema.json",
    "ergodicity_evidence": "ergodicity-evidence.schema.json",
    "nucleus_laws_evidence": "nucleus-laws-evidence.schema.json",
    "shuffle_equivalence_evidence": "shuffle-equivalence-evidence.schema.json",
    "observation_equivalence": "observation-equivalence.schema.json",
    "observation_equivalence_evidence": "observation-equivalence-evidence.schema.json",
    "normalized_observation_evidence": "normalized-observation-evidence.schema.json",
    "stabilized_observation_evidence": "stabilized-observation-evidence.schema.json",
    "measured_observation_evidence": "measured-observation-evidence.schema.json",
    "system_laws_evidence": "system_laws_evidence.schema.json",
    "runbook_laws_evidence": "runbook_laws_evidence.schema.json",
    "judgment_laws_evidence": "judgment-laws-evidence.schema.json",
    "temporal_modality": "temporal-modality.schema.json",
    "temporal_modality_evidence": "temporal-modality-evidence.schema.json",
    "measure_preservation_evidence": "measure-preservation-evidence.schema.json",
    "reduction_evidence": "reduction-evidence.schema.json",
    "syntax_recognition_evidence": "syntax-recognition-evidence.schema.json",
    "syntax_normal_form": "syntax-normal-form.schema.json",
    "judgment": "judgment.schema.json",
    "judgment_equivalence": "judgment-equivalence.schema.json",
    "evaluation_equivalence": "evaluation-equivalence.schema.json",
    "judgment_equivalence_evidence": "judgment-equivalence-evidence.schema.json",
    "evaluation_equivalence_evidence": "evaluation-equivalence-evidence.schema.json",
    "evaluated_observation": "evaluated-observation.schema.json",
    "evaluated_judgment": "evaluated-judgment.schema.json",
    "fixed_profile_evidence": "fixed-profile-evidence.schema.json",
    "presheaf_site": "presheaf-site.schema.json",
    "presheaf": "presheaf.schema.json",
    "sheafification_evidence": "sheafification-evidence.schema.json",
    "sheaf": "sheaf.schema.json",
    "context_geometry": "context-geometry.schema.json",
    "sheaf_profile_consistency_evidence": "sheaf-profile-consistency-evidence.schema.json",
    "substitution_map": "substitution-map.schema.json",
    "substitution_evidence": "substitution-evidence.schema.json",
    "eval_context_seed": "eval-context-seed.schema.json",
    "evaluation_frame": "evaluation-frame.schema.json",
    "evaluation_context": "evaluation-context.schema.json",
    "term_context": "term-context.schema.json",
    "reducibility_candidates": "reducibility-candidates.schema.json",
    "reducible_environment": "reducible-environment.schema.json",
    "trace_measure_evidence": "trace-measure-evidence.schema.json",
    "trace_observation_equivalence": "trace-observation-equivalence.schema.json",
    "trace_observation_equivalence_closure_evidence": "trace-observation-equivalence-closure-evidence.schema.json",
    "profile_observe_evidence": "profile-observe-evidence.schema.json",
    "fixed_observe_evidence": "fixed-observe-evidence.schema.json",
    "flow_measure_consistency_evidence": "flow-measure-consistency-evidence.schema.json",
    "profile_semantics_evidence": "profile-semantics-evidence.schema.json",
    "profile_dynamics_evidence": "profile-dynamics-evidence.schema.json",
    "reentry_trace_evidence": "reentry-trace-evidence.schema.json",
    "complete_trace_evidence": "complete-trace-evidence.schema.json",
    "decompose_trace_evidence": "decompose-trace-evidence.schema.json",
    "close_judgment_trace_evidence": "close-judgment-trace-evidence.schema.json",
    "head_trace_evidence": "head-trace-evidence.schema.json",
    "tail_trace_evidence": "tail-trace-evidence.schema.json",
    "trace_step_evidence": "trace-step-evidence.schema.json",
    "rehead_trace_evidence": "rehead-trace-evidence.schema.json",
    "retail_trace_evidence": "retail-trace-evidence.schema.json",
    "restep_trace_evidence": "restep-trace-evidence.schema.json",
    "continue_trace_evidence": "continue-trace-evidence.schema.json",
    "fixed_operator": "fixed-operator.schema.json",
    "comonad_derivative": "comonad-derivative.schema.json",
    "fixed_profile": "fixed-profile.schema.json",
    "trace_profile": "trace-profile.schema.json",
    "profile_semantics": "profile-semantics.schema.json",
    "profile_context": "profile-context.schema.json",
    "profile_invariant": "profile-invariant.schema.json",
    "profile_reach": "profile-reach.schema.json",
    "profile_entropy": "profile-entropy.schema.json",
    "shuffle_profile": "shuffle-profile.schema.json",
    "shuffle_geometry": "shuffle-geometry.schema.json",
    "fixed_shape": "fixed-shape.schema.json",
    "deviation_operator": "deviation-operator.schema.json",
    "profile_dynamics": "profile-dynamics.schema.json",
    "profile_syntax": "profile-syntax.schema.json",
    "fixed_finite_limits": "fixed-finite-limits.schema.json",
    "equate_judgment_observation_evidence": "equate-judgment-observation-evidence.schema.json",
    "flow_observation_map": "flow-observation-map.schema.json",
}


class LawValidationError(Exception):
    """Raised when a law mandated by the acts fails."""


@dataclass(frozen=True)
class LatticeOps:
    elements: set[str]
    order: Mapping[str, list[str]]
    meet_table: Mapping[str, Mapping[str, str]]
    join_table: Mapping[str, Mapping[str, str]]
    imply_table: Mapping[str, Mapping[str, str]]
    negate_map: Mapping[str, str]
    bottom: str
    top: str

    def leq(self, a: str, b: str) -> bool:
        """
        Order relation: a <= b iff b is listed in order[a].
        """
        return b in self.order.get(a, [])

    def meet(self, a: str, b: str) -> str:
        try:
            return self.meet_table[a][b]
        except Exception as exc:  # pragma: no cover - validated separately
            raise LawValidationError(f"missing meet entry for ({a},{b})") from exc

    def join(self, a: str, b: str) -> str:
        try:
            return self.join_table[a][b]
        except Exception as exc:  # pragma: no cover - validated separately
            raise LawValidationError(f"missing join entry for ({a},{b})") from exc

    def imply(self, a: str, b: str) -> str:
        try:
            return self.imply_table[a][b]
        except Exception as exc:  # pragma: no cover - validated separately
            raise LawValidationError(f"missing imply entry for ({a},{b})") from exc


def _require_elements(container: Mapping[str, Any], elements: set[str], context: str) -> None:
    for key, value in container.items():
        if key not in elements:
            raise LawValidationError(f"{context}: unknown element key {key}")
        if isinstance(value, str) and value not in elements:
            raise LawValidationError(f"{context}: value {value} not in elements")
        if isinstance(value, list):
            for item in value:
                if item not in elements:
                    raise LawValidationError(f"{context}: value {item} not in elements")
        if isinstance(value, Mapping):
            _require_elements(value, elements, context)


def _validate_order(elements: set[str], order: Mapping[str, list[str]], bottom: str, top: str) -> None:
    if set(order.keys()) != elements:
        raise LawValidationError("order table must have an entry for every element")
    for elt, uppers in order.items():
        if elt not in uppers:
            raise LawValidationError(f"order not reflexive at {elt}")
        for target in uppers:
            if target not in elements:
                raise LawValidationError(f"order references unknown element {target}")
    # Antisymmetry and transitivity
    for a, b in itertools.product(elements, repeat=2):
        if b in order[a] and a in order[b] and a != b:
            raise LawValidationError(f"order violates antisymmetry between {a} and {b}")
    for a, b, c in itertools.product(elements, repeat=3):
        if b in order[a] and c in order[b] and c not in order[a]:
            raise LawValidationError(f"order not transitive for {a} <= {b} <= {c}")
    # Bottom and top coherence
    if set(order[bottom]) != elements:
        raise LawValidationError("bottom must be below all elements")
    for elt in elements:
        if top not in order[elt]:
            raise LawValidationError("top must be above all elements")


def _require_total_binary(table: Mapping[str, Mapping[str, str]], elements: set[str], name: str) -> None:
    if set(table.keys()) != elements:
        raise LawValidationError(f"{name} table must have an entry for every left operand")
    for left, row in table.items():
        if set(row.keys()) != elements:
            raise LawValidationError(f"{name} row for {left} must have every right operand")
        for right, result in row.items():
            if result not in elements:
                raise LawValidationError(f"{name}({left},{right}) -> {result} not in elements")


def _check_commutative(table: Mapping[str, Mapping[str, str]], name: str) -> None:
    for a, b in itertools.product(table.keys(), repeat=2):
        if table[a][b] != table[b][a]:
            raise LawValidationError(f"{name} not commutative on ({a},{b})")


def _check_associative(op: callable, elements: set[str], name: str) -> None:
    for a, b, c in itertools.product(elements, repeat=3):
        if op(op(a, b), c) != op(a, op(b, c)):
            raise LawValidationError(f"{name} not associative on ({a},{b},{c})")


def _check_absorption(lat: LatticeOps) -> None:
    for a, b in itertools.product(lat.elements, repeat=2):
        if lat.meet(a, lat.join(a, b)) != a:
            raise LawValidationError(f"absorption fails: meet(a, join(a,b)) != a for {a}, {b}")
        if lat.join(a, lat.meet(a, b)) != a:
            raise LawValidationError(f"absorption fails: join(a, meet(a,b)) != a for {a}, {b}")


def _check_distributive(lat: LatticeOps) -> None:
    for a, b, c in itertools.product(lat.elements, repeat=3):
        left = lat.meet(a, lat.join(b, c))
        right = lat.join(lat.meet(a, b), lat.meet(a, c))
        if left != right:
            raise LawValidationError(f"meet distributes over join fails for {a},{b},{c}")
        left = lat.join(a, lat.meet(b, c))
        right = lat.meet(lat.join(a, b), lat.join(a, c))
        if left != right:
            raise LawValidationError(f"join distributes over meet fails for {a},{b},{c}")


def _check_implication(lat: LatticeOps) -> None:
    bottom = lat.bottom
    for x, y, z in itertools.product(lat.elements, repeat=3):
        meet_xy = lat.meet(x, y)
        left = lat.leq(meet_xy, z)
        right = lat.leq(x, lat.imply(y, z))
        if left != right:
            raise LawValidationError(f"implication adjunction fails for ({x},{y},{z})")
    for x in lat.elements:
        neg = lat.imply(x, bottom)
        if neg != lat.negate_map.get(x):
            raise LawValidationError(f"negation does not match implication for {x}")
    for x in lat.elements:
        if lat.meet(x, lat.negate_map[x]) != bottom:
            raise LawValidationError(f"negation not disjoint from {x}")


def validate_lattice(payload: Mapping[str, Any]) -> None:
    """
    Enforce finite judgment lattice laws on a carrier payload.
    """
    elements = set(payload["elements"])
    lat = LatticeOps(
        elements=elements,
        order=payload["order"],
        meet_table=payload["meet_table"],
        join_table=payload["join_table"],
        imply_table=payload["imply_table"],
        negate_map=payload["negate_map"],
        bottom=payload["bottom"],
        top=payload["top"],
    )
    if lat.bottom not in elements or lat.top not in elements:
        raise LawValidationError("bottom/top must be elements")
    _validate_order(elements, lat.order, lat.bottom, lat.top)
    _require_total_binary(lat.meet_table, elements, "meet")
    _require_total_binary(lat.join_table, elements, "join")
    _require_total_binary(lat.imply_table, elements, "imply")
    _require_elements(lat.negate_map, elements, "negation")
    _check_commutative(lat.meet_table, "meet")
    _check_commutative(lat.join_table, "join")
    _check_associative(lat.meet, elements, "meet")
    _check_associative(lat.join, elements, "join")
    _check_absorption(lat)
    _check_distributive(lat)
    _check_implication(lat)


def validate_profile_topos(payload: Mapping[str, Any]) -> None:
    """
    Enforce subobject classifier and finite-limits coherence for a profile_topos.

    This operates purely on the carrier data available in the profile_topos
    object:
    - The classifier truth/falsehood elements must coincide with top/bottom.
    - The classifier and limits must reference only lattice elements.
    - The terminal object must coincide with the lattice top.
    """
    elements = set(payload["elements"])
    bottom = payload["bottom"]
    top = payload["top"]

    # Subobject classifier coherence.
    classifier = payload.get("subobject_classifier", {})
    truth = classifier.get("truth")
    falsehood = classifier.get("falsehood")
    if truth is None or falsehood is None:
        raise LawValidationError("subobject_classifier must provide both truth and falsehood")
    if truth not in elements:
        raise LawValidationError("subobject_classifier.truth must be a lattice element")
    if falsehood not in elements:
        raise LawValidationError("subobject_classifier.falsehood must be a lattice element")
    if truth != top:
        raise LawValidationError("subobject_classifier.truth must equal top element")
    if falsehood != bottom:
        raise LawValidationError("subobject_classifier.falsehood must equal bottom element")
    # Characteristic maps, when present, must classify into lattice elements.
    characteristic = classifier.get("characteristic", {})
    for key, value in characteristic.items():
        if value not in elements:
            raise LawValidationError(
                f"subobject_classifier.characteristic[{key!r}] = {value!r} is not a lattice element"
            )

    # Finite limits coherence.
    finite_limits = payload.get("finite_limits", {})
    terminal = finite_limits.get("terminal")
    if terminal is None:
        raise LawValidationError("finite_limits must provide a terminal object")
    if terminal not in elements:
        raise LawValidationError("finite_limits.terminal must be a lattice element")
    if terminal != top:
        raise LawValidationError("finite_limits.terminal must equal top element")
    products = finite_limits.get("products", {})
    for key, value in products.items():
        if value not in elements:
            raise LawValidationError(
                f"finite_limits.products[{key!r}] = {value!r} is not a lattice element"
            )


def validate_trace(payload: Mapping[str, Any]) -> None:
    """
    Enforce trace head/tail recursion and shuffle metadata sanity.
    """
    elements = payload["elements"]
    head = payload["head"]
    tail = payload.get("tail", [])
    if not elements:
        raise LawValidationError("trace must contain at least one element")
    if elements[0] != head:
        raise LawValidationError("head must be the first element of the trace")
    if elements[1:] != tail:
        raise LawValidationError("tail must be elements after head")
    shuffle = payload.get("shuffle_metadata")
    if shuffle:
        perms = shuffle.get("permutations", [])
        for perm in perms:
            if sorted(perm) != list(range(len(elements))):
                raise LawValidationError("shuffle permutation must be full-length bijection")
        canonical = shuffle.get("canonical_rep")
        if canonical is not None and canonical not in elements:
            raise LawValidationError("shuffle canonical_rep must reference an element in trace")


def validate_nucleus_laws_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for nucleus_laws_evidence.

    The checks object must enumerate all required laws, and the global status
    must agree with the per-law flags. When status == \"pass\", no
    counterexample should be recorded; when status == \"fail\", a
    counterexample must be present.
    """
    checks = payload.get("checks", {})
    required = {"extensive", "idempotent", "monotone", "equalize", "absorb"}
    if set(checks.keys()) != required:
        missing = required - set(checks.keys())
        extra = set(checks.keys()) - required
        parts: list[str] = []
        if missing:
            parts.append(f"missing checks: {sorted(missing)}")
        if extra:
            parts.append(f"unexpected checks: {sorted(extra)}")
        raise LawValidationError(f"nucleus_laws_evidence.checks incomplete: {'; '.join(parts)}")
    all_pass = all(bool(checks[name]) for name in required)
    status = payload.get("status")
    if all_pass and status != "pass":
        raise LawValidationError("nucleus_laws_evidence.status must be 'pass' when all checks are true")
    if (not all_pass) and status != "fail":
        raise LawValidationError("nucleus_laws_evidence.status must be 'fail' when some check is false")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError("nucleus_laws_evidence with status 'pass' must not include a counterexample")
    if status == "fail" and not has_counterexample:
        raise LawValidationError("nucleus_laws_evidence with status 'fail' must include a counterexample")


def validate_flow_laws_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for flow_laws_evidence.

    The checks object must enumerate all required laws, and the global status
    must agree with the per-law flags. When status == \"pass\", no
    counterexample should be recorded; when status == \"fail\", a
    counterexample must be present.
    """
    checks = payload.get("checks", {})
    required = {"monotone", "inflationary", "distributive"}
    if set(checks.keys()) != required:
        missing = required - set(checks.keys())
        extra = set(checks.keys()) - required
        parts: list[str] = []
        if missing:
            parts.append(f"missing checks: {sorted(missing)}")
        if extra:
            parts.append(f"unexpected checks: {sorted(extra)}")
        raise LawValidationError(f"flow_laws_evidence.checks incomplete: {'; '.join(parts)}")
    all_pass = all(bool(checks[name]) for name in required)
    status = payload.get("status")
    if all_pass and status != "pass":
        raise LawValidationError("flow_laws_evidence.status must be 'pass' when all checks are true")
    if (not all_pass) and status != "fail":
        raise LawValidationError("flow_laws_evidence.status must be 'fail' when some check is false")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError("flow_laws_evidence with status 'pass' must not include a counterexample")
    if status == "fail" and not has_counterexample:
        raise LawValidationError("flow_laws_evidence with status 'fail' must include a counterexample")


def validate_temporal_modality(payload: Mapping[str, Any]) -> None:
    """
    Enforce basic structural consistency for temporal_modality carriers.

    The basis must be non-empty; always_table and eventually_table must
    define total maps on the basis, and their images must lie in the basis.
    """
    basis = payload.get("basis")
    if not isinstance(basis, list) or not basis:
        raise LawValidationError("temporal_modality.basis must be a non-empty list")
    basis_set = set(basis)
    always_table = payload.get("always_table")
    eventually_table = payload.get("eventually_table")
    if not isinstance(always_table, Mapping) or not isinstance(eventually_table, Mapping):
        raise LawValidationError("temporal_modality always_table and eventually_table must be mappings")
    if set(always_table.keys()) != basis_set:
        raise LawValidationError("temporal_modality.always_table keys must match basis exactly")
    if set(eventually_table.keys()) != basis_set:
        raise LawValidationError("temporal_modality.eventually_table keys must match basis exactly")
    for src, tgt in always_table.items():
        if tgt not in basis_set:
            raise LawValidationError(
                f"temporal_modality.always_table[{src!r}] maps to value {tgt!r} outside basis"
            )
    for src, tgt in eventually_table.items():
        if tgt not in basis_set:
            raise LawValidationError(
                f"temporal_modality.eventually_table[{src!r}] maps to value {tgt!r} outside basis"
            )


def validate_temporal_modality_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for temporal_modality_evidence.

    The residuation_table must enumerate all checked pairs, and the global
    status must agree with the per-entry lhs/rhs comparison. When
    status == \"pass\", no counterexample should be recorded; when
    status == \"fail\", a counterexample must be present and reference a
    failing entry.
    """
    table = payload.get("residuation_table")
    if not isinstance(table, list) or not table:
        raise LawValidationError("temporal_modality_evidence.residuation_table must be a non-empty list")
    any_failure = False
    for entry in table:
        if not isinstance(entry, Mapping):
            raise LawValidationError("each residuation_table entry must be a mapping")
        lhs = entry.get("lhs")
        rhs = entry.get("rhs")
        if not isinstance(lhs, bool) or not isinstance(rhs, bool):
            raise LawValidationError("residuation_table entries must provide boolean lhs and rhs")
        if lhs != rhs and not any_failure:
            any_failure = True
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("temporal_modality_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass":
        if any_failure:
            raise LawValidationError(
                "temporal_modality_evidence.status must be 'fail' when some residuation entries disagree"
            )
        if has_counterexample:
            raise LawValidationError(
                "temporal_modality_evidence with status 'pass' must not include a counterexample"
            )
    else:
        if not any_failure:
            raise LawValidationError(
                "temporal_modality_evidence.status must be 'pass' when all residuation entries agree"
            )
        if not has_counterexample:
            raise LawValidationError(
                "temporal_modality_evidence with status 'fail' must include a counterexample"
            )
        counterexample = payload["counterexample"]
        if not isinstance(counterexample, Mapping):
            raise LawValidationError("temporal_modality_evidence.counterexample must be a mapping")
        lhs = counterexample.get("lhs")
        rhs = counterexample.get("rhs")
        if lhs == rhs:
            raise LawValidationError(
                "temporal_modality_evidence.counterexample must record a failing residuation entry"
            )


def validate_trace_measure_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for trace_measure_evidence.

    Status must be 'pass' or 'fail'; when status == 'fail', a counterexample
    must be present. The evidence must record the trace and measurement_frame
    IDs it summarizes, and may optionally reference a concrete
    flow_measure_step via flow_measure_step_id.
    """
    trace_id = payload.get("trace_id")
    measurement_frame_id = payload.get("measurement_frame_id")
    if not isinstance(trace_id, str):
        raise LawValidationError("trace_measure_evidence.trace_id must be a string")
    if not isinstance(measurement_frame_id, str):
        raise LawValidationError("trace_measure_evidence.measurement_frame_id must be a string")
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("trace_measure_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "trace_measure_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "trace_measure_evidence with status 'fail' must include a counterexample"
        )


def validate_profile_observe_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for profile_observe_evidence.

    Status must be 'pass' or 'fail'; when status == 'fail', a counterexample
    must be present; when status == 'pass', no counterexample may be present.
    """
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("profile_observe_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "profile_observe_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "profile_observe_evidence with status 'fail' must include a counterexample"
        )


def validate_fixed_observe_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for fixed_observe_evidence.

    Status must be 'pass' or 'fail'; when status == 'fail', a counterexample
    must be present; when status == 'pass', no counterexample may be present.
    """
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("fixed_observe_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "fixed_observe_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "fixed_observe_evidence with status 'fail' must include a counterexample"
        )


def validate_flow_measure_consistency_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for flow_measure_consistency_evidence.

    Status must be 'pass' or 'fail'; when status == 'fail', a counterexample
    must be present; when status == 'pass', no counterexample may be present.
    """
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("flow_measure_consistency_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "flow_measure_consistency_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "flow_measure_consistency_evidence with status 'fail' must include a counterexample"
        )


def validate_profile_semantics_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for profile_semantics_evidence.

    The checks object must enumerate the required classifier/limits checks,
    and the global status must agree with the presence of counterexamples.
    """
    checks = payload.get("checks")
    if not isinstance(checks, Mapping):
        raise LawValidationError("profile_semantics_evidence.checks must be a mapping")
    required = {"classifier_truth_falsehood", "classifier_elements", "terminal_matches_top"}
    if set(checks.keys()) != required:
        missing = required - set(checks.keys())
        extra = set(checks.keys()) - required
        parts: list[str] = []
        if missing:
            parts.append(f"missing checks: {sorted(missing)}")
        if extra:
            parts.append(f"unexpected checks: {sorted(extra)}")
        raise LawValidationError(f"profile_semantics_evidence.checks incomplete: {'; '.join(parts)}")
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("profile_semantics_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "profile_semantics_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "profile_semantics_evidence with status 'fail' must include a counterexample"
        )


def validate_profile_dynamics_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for profile_dynamics_evidence.
    """
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("profile_dynamics_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "profile_dynamics_evidence with status 'pass' must not include a counterexample"
        )


def validate_reentry_trace_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for reentry_trace_evidence.

    Status must be 'pass' or 'fail'. When status == 'pass', no counterexample
    may be present; when status == 'fail', a counterexample must be present.
    The reentry_steps list must be present (possibly empty) and each entry
    must at least record an element, its class representative, and the
    equivalence class used for closure.
    """
    trace_id = payload.get("trace_id")
    if not isinstance(trace_id, str):
        raise LawValidationError("reentry_trace_evidence.trace_id must be a string")
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("reentry_trace_evidence.status must be 'pass' or 'fail'")
    steps = payload.get("reentry_steps")
    if not isinstance(steps, list):
        raise LawValidationError("reentry_trace_evidence.reentry_steps must be a list")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "reentry_trace_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "reentry_trace_evidence with status 'fail' must include a counterexample"
        )


def validate_complete_trace_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for complete_trace_evidence.

    Status must be 'pass' or 'fail'. When status == 'pass', the steps list
    must be non-empty and no counterexample may be present. When status ==
    'fail', a counterexample must be present.
    """
    trace_id = payload.get("trace_id")
    if not isinstance(trace_id, str):
        raise LawValidationError("complete_trace_evidence.trace_id must be a string")
    steps = payload.get("steps")
    if not isinstance(steps, list):
        raise LawValidationError("complete_trace_evidence.steps must be a list")
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("complete_trace_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass":
        if not steps:
            raise LawValidationError(
                "complete_trace_evidence with status 'pass' must include at least one step"
            )
        if has_counterexample:
            raise LawValidationError(
                "complete_trace_evidence with status 'pass' must not include a counterexample"
            )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "complete_trace_evidence with status 'fail' must include a counterexample"
        )


def validate_fixed_operator(payload: Mapping[str, Any], objects_by_id: Mapping[str, dict] | None = None) -> None:
    """
    Enforce internal consistency for fixed_operator carriers.

    The operator_table must be total on elements and closed in the carrier
    lattice; when a fixed_invariants carrier is available via objects_by_id,
    its elements must match the fixed_operator elements and carrier_id.
    """
    elements = payload.get("elements")
    table = payload.get("operator_table")
    if not isinstance(elements, list) or not elements:
        raise LawValidationError("fixed_operator.elements must be a non-empty list")
    elem_set = set(elements)
    if not isinstance(table, Mapping):
        raise LawValidationError("fixed_operator.operator_table must be a mapping")
    if set(table.keys()) != elem_set:
        raise LawValidationError("fixed_operator.operator_table must have an entry for every element")
    for src, tgt in table.items():
        if tgt not in elem_set:
            raise LawValidationError(
                f"fixed_operator.operator_table maps {src!r} to {tgt!r} outside elements"
            )
    if objects_by_id is not None:
        carrier_id = payload.get("carrier_id")
        carrier = objects_by_id.get(str(carrier_id))
        if carrier is None or carrier.get("kind") != "fixed_invariants":
            raise LawValidationError(
                "fixed_operator.carrier_id must reference a fixed_invariants object when available"
            )
        fixed_elements = set(carrier.get("elements", []))
        if elem_set != fixed_elements:
            raise LawValidationError(
                "fixed_operator.elements must equal fixed_invariants.elements when a carrier is available"
            )


def validate_comonad_derivative(payload: Mapping[str, Any], objects_by_id: Mapping[str, dict] | None = None) -> None:
    """
    Enforce internal consistency for comonad_derivative carriers.

    The derivative_table must be total on elements and closed in the carrier
    lattice; when a fixed_invariants carrier is available via objects_by_id,
    its elements must match the comonad_derivative elements and carrier_id.
    """
    elements = payload.get("elements")
    table = payload.get("derivative_table")
    if not isinstance(elements, list) or not elements:
        raise LawValidationError("comonad_derivative.elements must be a non-empty list")
    elem_set = set(elements)
    if not isinstance(table, Mapping):
        raise LawValidationError("comonad_derivative.derivative_table must be a mapping")
    if set(table.keys()) != elem_set:
        raise LawValidationError(
            "comonad_derivative.derivative_table must have an entry for every element"
        )
    for src, tgt in table.items():
        if tgt not in elem_set:
            raise LawValidationError(
                f"comonad_derivative.derivative_table maps {src!r} to {tgt!r} outside elements"
            )
    if objects_by_id is not None:
        carrier_id = payload.get("carrier_id")
        carrier = objects_by_id.get(str(carrier_id))
        if carrier is None or carrier.get("kind") != "fixed_invariants":
            raise LawValidationError(
                "comonad_derivative.carrier_id must reference a fixed_invariants object when available"
            )
        fixed_elements = set(carrier.get("elements", []))
        if elem_set != fixed_elements:
            raise LawValidationError(
                "comonad_derivative.elements must equal fixed_invariants.elements when a carrier is available"
            )


def validate_equate_judgment_observation_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for equate_judgment_observation_evidence.

    Requirements:
    - status is 'pass' or 'fail';
    - when status is 'pass', no counterexample may be present;
    - when status is 'fail', a counterexample must be present.
    """
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("equate_judgment_observation_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "equate_judgment_observation_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "equate_judgment_observation_evidence with status 'fail' must include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "profile_dynamics_evidence with status 'fail' must include a counterexample"
        )


def validate_measure_preservation_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for measure_preservation_evidence.

    Status must be one of {preserving, dissipative, fail} and witnesses
    must be present as a mapping.
    """
    status = payload.get("status")
    if status not in {"preserving", "dissipative", "fail"}:
        raise LawValidationError("measure_preservation_evidence.status must be 'preserving', 'dissipative', or 'fail'")
    witnesses = payload.get("witnesses")
    if not isinstance(witnesses, Mapping):
        raise LawValidationError("measure_preservation_evidence.witnesses must be a mapping")


def validate_judgment_laws_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for judgment_laws_evidence.

    The law_checks array must enumerate all required judgment lattice laws,
    each with a per-law status, and the global status must agree with the
    per-law statuses. When status == \"pass\", no counterexamples may be
    present; when status == \"fail\", at least one counterexample must be
    present on some failing law.
    """
    law_checks = payload.get("law_checks")
    if not isinstance(law_checks, list) or not law_checks:
        raise LawValidationError("judgment_laws_evidence.law_checks must be a non-empty list")
    required_laws = {"order", "meet_join", "implication", "negation", "bounds"}
    seen_laws: set[str] = set()
    any_counterexample = False
    for entry in law_checks:
        if not isinstance(entry, Mapping):
            raise LawValidationError("each law_checks entry must be a mapping")
        law = entry.get("law")
        status = entry.get("status")
        if law not in required_laws:
            raise LawValidationError(f"unexpected law_checks law {law!r}")
        if law in seen_laws:
            raise LawValidationError(f"duplicate law_checks entry for law {law!r}")
        seen_laws.add(law)
        if status not in {"pass", "fail"}:
            raise LawValidationError(
                f"judgment_laws_evidence.law_checks[{law!r}].status must be 'pass' or 'fail'"
            )
        has_ce = "counterexample" in entry and entry["counterexample"] is not None
        if status == "pass" and has_ce:
            raise LawValidationError(
                f"judgment_laws_evidence law {law!r} with status 'pass' must not include a counterexample"
            )
        if status == "fail" and has_ce:
            any_counterexample = True
    if seen_laws != required_laws:
        missing = required_laws - seen_laws
        extra = seen_laws - required_laws
        parts: list[str] = []
        if missing:
            parts.append(f"missing laws: {sorted(missing)}")
        if extra:
            parts.append(f"unexpected laws: {sorted(extra)}")
        raise LawValidationError(
            "judgment_laws_evidence.law_checks incomplete: " + "; ".join(parts)
        )
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("judgment_laws_evidence.status must be 'pass' or 'fail'")
    if status == "pass" and any(entry.get("status") == "fail" for entry in law_checks):
        raise LawValidationError(
            "judgment_laws_evidence.status must be 'pass' when all law_checks statuses are 'pass'"
        )
    if status == "fail":
        if all(entry.get("status") == "pass" for entry in law_checks):
            raise LawValidationError(
                "judgment_laws_evidence.status must be 'pass' when all law_checks statuses are 'pass'"
            )
        if not any_counterexample:
            raise LawValidationError(
                "judgment_laws_evidence.status 'fail' requires at least one law_checks counterexample"
            )


def validate_system_laws_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for system_laws_evidence.

    The checks object must enumerate all required system-level laws, and the
    global status must agree with the per-law flags. When status == \"pass\",
    no counterexample should be recorded; when status == \"fail\", a
    counterexample must be present.
    """
    checks = payload.get("checks", {})
    required = {
        "profile_phase_fixed_lattice_alignment",
        "flow_nucleus_carrier_alignment",
        "fixed_invariants_fixed_points",
        "measurement_frame_recognition_alignment",
        "observation_equivalence_coverage",
        "trace_alignment",
        "regime_operator_completeness",
    }
    if set(checks.keys()) != required:
        missing = required - set(checks.keys())
        extra = set(checks.keys()) - required
        parts: list[str] = []
        if missing:
            parts.append(f"missing checks: {sorted(missing)}")
        if extra:
            parts.append(f"unexpected checks: {sorted(extra)}")
        raise LawValidationError(f"system_laws_evidence.checks incomplete: {'; '.join(parts)}")
    all_pass = all(bool(checks[name]) for name in required)
    status = payload.get("status")
    if all_pass and status != "pass":
        raise LawValidationError("system_laws_evidence.status must be 'pass' when all checks are true")
    if (not all_pass) and status != "fail":
        raise LawValidationError("system_laws_evidence.status must be 'fail' when some check is false")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError("system_laws_evidence with status 'pass' must not include a counterexample")
    if status == "fail" and not has_counterexample:
        raise LawValidationError("system_laws_evidence with status 'fail' must include a counterexample")


def validate_runbook_laws_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for runbook_laws_evidence.

    The checks object must enumerate all required runbook-level laws, and the
    global status must agree with the per-law flags. When status == \"pass\",
    no counterexample should be recorded; when status == \"fail\", a
    counterexample must be present.
    """
    checks = payload.get("checks", {})
    required = {
        "inputs_satisfied",
        "outputs_lawful",
        "composition_typed",
        "operator_order_lawful",
        "bindings_consistent",
        "declared_outputs_match",
        "regime_respected",
        "no_illegal_transitions",
    }
    if set(checks.keys()) != required:
        missing = required - set(checks.keys())
        extra = set(checks.keys()) - required
        parts: list[str] = []
        if missing:
            parts.append(f"missing checks: {sorted(missing)}")
        if extra:
            parts.append(f"unexpected checks: {sorted(extra)}")
        raise LawValidationError(f"runbook_laws_evidence.checks incomplete: {'; '.join(parts)}")
    all_pass = all(bool(checks[name]) for name in required)
    status = payload.get("status")
    if all_pass and status != "pass":
        raise LawValidationError("runbook_laws_evidence.status must be 'pass' when all checks are true")
    if (not all_pass) and status != "fail":
        raise LawValidationError("runbook_laws_evidence.status must be 'fail' when some check is false")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError("runbook_laws_evidence with status 'pass' must not include a counterexample")
    if status == "fail" and not has_counterexample:
        raise LawValidationError("runbook_laws_evidence with status 'fail' must include a counterexample")


def validate_against_schema(payload: Mapping[str, Any], schema_name: str) -> None:
    """
    Validate ``payload`` against the named JSON/YAML schema.

    This function performs *only* structural/schema checks: it does not
    enforce any of the algebraic laws from the Acts. It is the lowest
    layer in the validation stack that other helpers build upon.
    """
    schema = load_schema(schema_name)
    jsonschema.validate(payload, schema)


def validate_object(payload: MutableMapping[str, Any]) -> None:
    """
    Validate a single carrier payload against its schema and local laws.

    Pipeline:
    - Schema validation via :func:`validate_against_schema`.
    - Canonical ID coherence via :func:`assert_id_coherence`.
    - *Carrier-local* law checks (finite lattices, trace recursion,
      observation equivalence partitions, etc.).

    This helper intentionally does **not** enforce graph-level laws that
    require multiple carriers or AOG context (Flow/Nucleus/System
    commutation, geometry_profile, runbook laws). Those live in
    :mod:`relationality.law_enforcement` and are exercised via
    dedicated law-check runbooks.
    """
    kind = payload.get("kind")
    if kind not in OBJECT_SCHEMAS:
        raise ValueError(f"unknown object kind {kind}")
    validate_against_schema(payload, OBJECT_SCHEMAS[kind])
    assert_id_coherence(payload)
    if kind == "profile_topos":
        validate_lattice(payload)
        validate_profile_topos(payload)
    if kind == "fixed_invariants":
        validate_lattice(payload)
    if kind == "phase_space":
        # Phase space is a full finite judgment lattice over its states.
        validate_lattice(payload | {"elements": payload["states"]})
        if payload["current_state"] not in set(payload["states"]):
            raise LawValidationError("current_state must be one of the phase_space states")
        if not payload.get("flow_tags"):
            raise LawValidationError("phase_space must declare at least one flow_tag")
    if kind == "trace":
        validate_trace(payload)
    if kind == "flow_laws_evidence":
        validate_flow_laws_evidence(payload)
    if kind == "judgment_laws_evidence":
        validate_judgment_laws_evidence(payload)
    if kind == "temporal_modality":
        validate_temporal_modality(payload)
    if kind == "temporal_modality_evidence":
        validate_temporal_modality_evidence(payload)
    if kind == "measure_preservation_evidence":
        validate_measure_preservation_evidence(payload)
    if kind == "nucleus_laws_evidence":
        validate_nucleus_laws_evidence(payload)
    if kind == "trace_measure_evidence":
        validate_trace_measure_evidence(payload)
    if kind == "mixing_evidence":
        validate_mixing_evidence(payload)
    if kind == "ergodicity_evidence":
        validate_ergodicity_evidence(payload)
    if kind == "shuffle_equivalence_evidence":
        validate_shuffle_equivalence_evidence(payload)
    if kind == "profile_observe_evidence":
        validate_profile_observe_evidence(payload)
    if kind == "fixed_observe_evidence":
        validate_fixed_observe_evidence(payload)
    if kind == "flow_measure_consistency_evidence":
        validate_flow_measure_consistency_evidence(payload)
    if kind == "profile_semantics_evidence":
        validate_profile_semantics_evidence(payload)
    if kind == "profile_dynamics_evidence":
        validate_profile_dynamics_evidence(payload)
    if kind == "reentry_trace_evidence":
        validate_reentry_trace_evidence(payload)
    if kind == "complete_trace_evidence":
        validate_complete_trace_evidence(payload)
    if kind == "fixed_operator":
        # Objects-by-id context is not available here; the per-object check
        # only enforces table totality/closure. Global consistency with
        # fixed_invariants is handled by system-level law checks when needed.
        validate_fixed_operator(payload)
    if kind == "comonad_derivative":
        validate_comonad_derivative(payload)
    if kind == "equate_judgment_observation_evidence":
        validate_equate_judgment_observation_evidence(payload)
    if kind == "flow_map":
        validate_flow_map(payload)
    if kind == "flow_observation_map":
        validate_flow_observation_map(payload)
    if kind == "nucleus_map":
        validate_nucleus_map(payload)
    if kind == "regime":
        validate_regime(payload)
    if kind == "observation_equivalence":
        validate_observation_equivalence(payload)
    if kind == "observation_equivalence_evidence":
        validate_observation_equivalence_evidence(payload)
    if kind == "evaluation_equivalence":
        validate_evaluation_equivalence(payload)
    if kind == "evaluation_equivalence_evidence":
        validate_evaluation_equivalence_evidence(payload)
    if kind == "judgment_equivalence":
        validate_judgment_equivalence(payload)
    if kind == "fixed_profile_evidence":
        validate_fixed_profile_evidence(payload)
    if kind == "measured_observation_evidence":
        validate_measured_observation_evidence(payload)
    if kind == "normalized_observation_evidence":
        validate_normalized_observation_evidence(payload)
    if kind == "stabilized_observation_evidence":
        validate_stabilized_observation_evidence(payload)
    if kind == "system_laws_evidence":
        validate_system_laws_evidence(payload)
    if kind == "runbook_laws_evidence":
        validate_runbook_laws_evidence(payload)
    if kind == "spectral_geometry":
        validate_spectral_geometry(payload)
    if kind == "observation_kernel":
        validate_observation_kernel(payload)
    if kind == "fixed_kernel":
        validate_fixed_kernel(payload)
    if kind == "substitution_evidence":
        validate_substitution_evidence(payload)
    if kind == "evaluation_context":
        validate_evaluation_context(payload)
    if kind == "reducible_environment":
        validate_reducible_environment(payload)
    if kind == "presheaf_site":
        validate_presheaf_site(payload)
    if kind == "presheaf":
        validate_presheaf(payload)
    if kind == "sheafification_evidence":
        validate_sheafification_evidence(payload)
    if kind == "sheaf":
        validate_sheaf(payload)
    if kind == "context_geometry":
        validate_context_geometry(payload)
    if kind == "sheaf_profile_consistency_evidence":
        validate_sheaf_profile_consistency_evidence(payload)
    if kind == "regime":
        allowed = set(payload["allowed_operators"])
        suppressed = set(payload["suppressed_operators"])
        if allowed & suppressed:
            raise LawValidationError("allowed_operators and suppressed_operators must be disjoint")
    if kind == "measurement_frame":
        kernel_params = payload.get("kernel_params")
        if not isinstance(kernel_params, Mapping):
            raise LawValidationError("measurement_frame.kernel_params must be a mapping")
        carrier_map = kernel_params.get("carrier_to_element")
        if carrier_map is not None:
            if not isinstance(carrier_map, Mapping):
                raise LawValidationError("measurement_frame.kernel_params.carrier_to_element must be a mapping")
            for k, v in carrier_map.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise LawValidationError(
                        "measurement_frame.kernel_params.carrier_to_element must map strings to strings"
                    )
        constraints = payload.get("constraints")
        if not isinstance(constraints, Mapping):
            raise LawValidationError("measurement_frame.constraints must be a mapping")
        term_id = constraints.get("term_id") if constraints else None
        if term_id is not None and not isinstance(term_id, str):
            raise LawValidationError("measurement_frame.constraints.term_id must be a string when provided")
    if kind == "system":
        # Basic sanity: ensure referenced IDs are distinct to avoid aliasing mistakes.
        refs = {
            payload["profile_topos_id"],
            payload["phase_space_id"],
            payload["measurement_frame_id"],
            payload["regime_id"],
            payload["trace_id"],
            payload["fixed_invariants_id"],
        }
        if len(refs) != 6:
            raise LawValidationError("system references must be six distinct object IDs")


def validate_runbook(payload: MutableMapping[str, Any]) -> None:
    validate_against_schema(payload, "runbook.schema.yaml")
    assert_id_coherence(payload)
    indices = [step["step_index"] for step in payload["steps"]]
    if sorted(indices) != list(range(len(indices))):
        raise LawValidationError("runbook step_index values must be contiguous starting at 0")


def validate_flow_map(payload: Mapping[str, Any]) -> None:
    elements = set(payload["elements"])
    table = payload["flow_table"]
    if set(table.keys()) != elements:
        raise LawValidationError("flow_table must have an entry for every element")
    for src, tgt in table.items():
        if tgt not in elements:
            raise LawValidationError(f"flow_table maps {src} to unknown element {tgt}")


def validate_flow_observation_map(payload: Mapping[str, Any]) -> None:
    """
    Enforce basic shape constraints for a flow_observation_map carrier.

    This mirrors the structural part of FlowObservation: the flow_table must
    be a total, single-valued map on a finite set of observation IDs. Full
    flow laws (monotonicity, inflationary behaviour on the observation
    lattice) are enforced by the separate law-check infrastructure.
    """
    table = payload.get("flow_table") or {}
    if not isinstance(table, Mapping):
        raise LawValidationError("flow_observation_map.flow_table must be a mapping")
    # Require totality over its declared domain: keys and values are strings;
    # the domain is simply the set of keys present, and codomain values must
    # also lie in that finite set.
    keys = set(table.keys())
    if not keys:
        raise LawValidationError("flow_observation_map.flow_table must be non-empty")
    for src, tgt in table.items():
        if not isinstance(src, str) or not isinstance(tgt, str):
            raise LawValidationError("flow_observation_map.flow_table must map strings to strings")
        if tgt not in keys:
            raise LawValidationError(
                f"flow_observation_map.flow_table maps {src} to target {tgt} not in its domain"
            )


def validate_regime(payload: Mapping[str, Any]) -> None:
    """
    Enforce regime constraints:
    - allowed_operators and suppressed_operators are disjoint and drawn from
      the declared operator alphabet (runbook.schema.yaml).
    - required system_interaction operators are allowed and not suppressed.
    - invariant_constraints keys must look like fixed_invariants IDs; values
      must be booleans or lists of string elements.
    """
    allowed_ops = set(payload.get("allowed_operators") or [])
    suppressed_ops = set(payload.get("suppressed_operators") or [])
    if allowed_ops & suppressed_ops:
        raise LawValidationError("regime.allowed_operators and suppressed_operators must be disjoint")

    schema = load_schema("runbook.schema.yaml")
    operator_enum = set(schema["properties"]["steps"]["items"]["properties"]["operator"]["enum"])
    unknown = (allowed_ops | suppressed_ops) - operator_enum
    if unknown:
        raise LawValidationError(f"regime lists operators not declared in acts/runbook schema: {sorted(unknown)}")

    required_ops = {
        "observe",
        "nucleate_profile",
        "flow_profile",
        "flow_measure_step",
        "normalize_observation",
        "stabilize_observation",
        "fix_flow_nucleus",
    }
    missing = required_ops - allowed_ops
    suppressed_required = required_ops & suppressed_ops
    if missing or suppressed_required:
        raise LawValidationError(
            "regime must allow and not suppress all system_interaction operators "
            f"(missing={sorted(missing)}, suppressed={sorted(suppressed_required)})"
        )

    constraints = payload.get("invariant_constraints") or {}
    if not isinstance(constraints, Mapping):
        raise LawValidationError("regime.invariant_constraints must be a mapping")
    for key, value in constraints.items():
        if not isinstance(key, str) or not key.isalnum() or len(key) != 64:
            raise LawValidationError("regime.invariant_constraints keys must be hex fixed_invariants IDs")
        if isinstance(value, bool):
            continue
        if isinstance(value, list):
            if not all(isinstance(item, str) for item in value):
                raise LawValidationError("regime.invariant_constraints list entries must be strings")
            continue
        raise LawValidationError("regime.invariant_constraints values must be booleans or lists of strings")


def validate_nucleus_map(payload: Mapping[str, Any]) -> None:
    elements = set(payload["elements"])
    table = payload["nucleus_table"]
    if set(table.keys()) != elements:
        raise LawValidationError("nucleus_table must have an entry for every element")
    for src, tgt in table.items():
        if tgt not in elements:
            raise LawValidationError(f"nucleus_table maps {src} to unknown element {tgt}")


def validate_fixed_kernel(payload: Mapping[str, Any]) -> None:
    basis = payload["basis"]
    matrix = payload["kernel_matrix"]
    basis_size = len(basis)
    if basis_size == 0:
        raise LawValidationError("fixed_kernel basis must be non-empty")
    if len(matrix) != basis_size:
        raise LawValidationError("fixed_kernel kernel_matrix must have one row per basis element")
    for row in matrix:
        if len(row) != basis_size:
            raise LawValidationError("fixed_kernel kernel_matrix must be square with size equal to basis length")
    stationarity = payload.get("stationarity_evidence", {})
    space_average = stationarity.get("space_average")
    if not isinstance(space_average, list) or len(space_average) != basis_size:
        raise LawValidationError("fixed_kernel stationarity_evidence.space_average must have same length as basis")
    # Exact stationarity: space_average * kernel_matrix == space_average.
    # We interpret numbers as rational via their decimal representation to
    # avoid floating-point tolerances, as required by the acts.
    space_vector = [Fraction(str(value)) for value in space_average]
    kernel_rows = [[Fraction(str(entry)) for entry in row] for row in matrix]
    result_vector: list[Fraction] = []
    for column_index in range(basis_size):
        value = sum(
            space_vector[row_index] * kernel_rows[row_index][column_index]
            for row_index in range(basis_size)
        )
        result_vector.append(value)
    if result_vector != space_vector:
        raise LawValidationError("fixed_kernel stationarity_evidence.space_average is not a fixed point of kernel_matrix")


def validate_observation_kernel(payload: Mapping[str, Any]) -> None:
    """
    Enforce basic shape constraints for an observation_kernel carrier.

    The kernel_matrix must be a square matrix with dimension equal to the
    basis length. Stationarity evidence, when present, is not required to
    witness a fixed point here; that stricter requirement is reserved for
    fixed_kernel carriers.
    """
    basis = payload["basis"]
    matrix = payload["kernel_matrix"]
    basis_size = len(basis)
    if basis_size == 0:
        raise LawValidationError("observation_kernel basis must be non-empty")
    if len(matrix) != basis_size:
        raise LawValidationError("observation_kernel kernel_matrix must have one row per basis element")
    for row in matrix:
        if len(row) != basis_size:
            raise LawValidationError("observation_kernel kernel_matrix must be square with size equal to basis length")


def validate_mixing_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for mixing_evidence.

    When status == \"pass\", the entropy path must be monotone
    non-decreasing and no counterexample may be present. When
    status == \"fail\", a counterexample must be provided.
    """
    entropy_path = payload.get("entropy_path")
    if not isinstance(entropy_path, list) or not entropy_path:
        raise LawValidationError("mixing_evidence.entropy_path must be a non-empty list")
    # Use exact rational comparison based on the string representation.
    try:
        entropy_values = [Fraction(str(value)) for value in entropy_path]
    except Exception as exc:  # pragma: no cover - defensive
        raise LawValidationError("mixing_evidence.entropy_path entries must be valid rationals") from exc
    # Entropy values must lie in the closed interval [0,1].
    if any(value < 0 or value > 1 for value in entropy_values):
        raise LawValidationError("mixing_evidence.entropy_path values must lie in the interval [0,1]")

    status = payload.get("status")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    # Monotone non-decreasing entropy is required when mixing passes.
    is_monotone = all(
        earlier <= later
        for earlier, later in zip(entropy_values, entropy_values[1:])
    )
    if status == "pass":
        if not is_monotone:
            raise LawValidationError("mixing_evidence with status 'pass' must have non-decreasing entropy_path")
        if has_counterexample:
            raise LawValidationError("mixing_evidence with status 'pass' must not include a counterexample")
    elif status == "fail":
        if not has_counterexample:
            raise LawValidationError("mixing_evidence with status 'fail' must include a counterexample")
    else:
        raise LawValidationError("mixing_evidence.status must be 'pass' or 'fail'")


def validate_ergodicity_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for ergodicity_evidence.

    Status must agree with the element-wise comparison between
    time_average and space_average, and the counterexample (when
    present) must describe the first mismatch.
    """
    time_average_raw = payload.get("time_average")
    space_average_raw = payload.get("space_average")
    if not isinstance(time_average_raw, list) or not isinstance(space_average_raw, list):
        raise LawValidationError("ergodicity_evidence.time_average and space_average must be lists")
    if len(time_average_raw) == 0:
        raise LawValidationError("ergodicity_evidence.time_average must be non-empty")
    if len(time_average_raw) != len(space_average_raw):
        raise LawValidationError("ergodicity_evidence.time_average and space_average must have the same length")
    try:
        time_average = [Fraction(str(v)) for v in time_average_raw]
        space_average = [Fraction(str(v)) for v in space_average_raw]
    except Exception as exc:  # pragma: no cover - defensive
        raise LawValidationError(
            "ergodicity_evidence.time_average and space_average entries must be valid rationals"
        ) from exc
    status = payload.get("status")
    mismatch_index = None
    for index, (time_value, space_value) in enumerate(zip(time_average, space_average)):
        if time_value != space_value:
            mismatch_index = index
            break
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if mismatch_index is None:
        if status != "pass":
            raise LawValidationError("ergodicity_evidence.status must be 'pass' when all entries match")
        if has_counterexample:
            raise LawValidationError("ergodicity_evidence with status 'pass' must not include a counterexample")
    else:
        if status != "fail":
            raise LawValidationError("ergodicity_evidence.status must be 'fail' when a mismatch exists")
        if not has_counterexample:
            raise LawValidationError("ergodicity_evidence with status 'fail' must include a counterexample")
        counterexample = payload["counterexample"]
        if counterexample.get("index") != mismatch_index:
            raise LawValidationError("ergodicity_evidence.counterexample.index must match the first mismatch index")
        try:
            ce_time = Fraction(str(counterexample.get("time_value")))
            ce_space = Fraction(str(counterexample.get("space_value")))
        except Exception as exc:  # pragma: no cover - defensive
            raise LawValidationError(
                "ergodicity_evidence.counterexample time_value/space_value must be valid rationals"
            ) from exc
        if ce_time != time_average[mismatch_index]:
            raise LawValidationError(
                "ergodicity_evidence.counterexample.time_value must match time_average at the mismatch index"
            )
        if ce_space != space_average[mismatch_index]:
            raise LawValidationError(
                "ergodicity_evidence.counterexample.space_value must match space_average at the mismatch index"
            )


def validate_spectral_geometry(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for spectral_geometry carriers.

    Checks:
    - operator_matrices are square with dimension equal to basis length.
    - spectral_weights/harmonic_modes tables align with operator names.
    - for each operator and (weight, mode) pair, A v = λ v holds exactly using
      rational arithmetic based on the decimal representation.
    - spectral_weights are sorted in non-decreasing order for each operator.
    - harmonic_modes are normalized to unit norm with respect to the chosen
      numeric representation (sum of squares == 1).
    """
    basis = payload["basis"]
    basis_size = len(basis)
    if basis_size == 0:
        raise LawValidationError("spectral_geometry basis must be non-empty")
    op_mats = payload.get("operator_matrices", {})
    eigvals = payload.get("spectral_weights", {})
    eigvecs = payload.get("harmonic_modes", {})
    if not isinstance(op_mats, Mapping) or not op_mats:
        raise LawValidationError("spectral_geometry.operator_matrices must be a non-empty mapping")
    if not isinstance(eigvals, Mapping) or not isinstance(eigvecs, Mapping):
        raise LawValidationError("spectral_geometry.spectral_weights and harmonic_modes must be mappings")
    # Require spectral tables exactly for the operators we have matrices for.
    op_names = set(op_mats.keys())
    if set(eigvals.keys()) != op_names or set(eigvecs.keys()) != op_names:
        raise LawValidationError("spectral_geometry spectral_weights/harmonic_modes entries must match operator_matrices keys exactly")
    for name, matrix in op_mats.items():
        if len(matrix) != basis_size:
            raise LawValidationError(f"spectral_geometry operator {name!r} must have one row per basis element")
        for row in matrix:
            if len(row) != basis_size:
                raise LawValidationError(f"spectral_geometry operator {name!r} matrix must be square with size equal to basis length")
        values = eigvals[name]
        vectors = eigvecs[name]
        if len(values) != len(vectors):
            raise LawValidationError(f"spectral_geometry operator {name!r} must have the same number of spectral_weights and harmonic_modes")
        # Spectral weights must be sorted in non-decreasing order.
        value_fracs = [Fraction(str(v)) for v in values]
        if any(a > b for a, b in zip(value_fracs, value_fracs[1:])):
            raise LawValidationError(f"spectral_geometry spectral_weights for operator {name!r} must be sorted in non-decreasing order")
        # Check each (weight, mode) pair.
        # Treat harmonic modes as column vectors encoded as arrays of length |basis|.
        mat_frac = [[Fraction(str(entry)) for entry in row] for row in matrix]
        for idx, (lam, vec) in enumerate(zip(value_fracs, vectors)):
            if len(vec) != basis_size:
                raise LawValidationError(
                    f"spectral_geometry harmonic_mode {idx} for operator {name!r} must have length equal to basis size"
                )
            v = [Fraction(str(entry)) for entry in vec]
            # Unit-norm requirement: sum_i v_i^2 == 1.
            norm_sq = sum(component * component for component in v)
            if norm_sq != Fraction(1):
                raise LawValidationError(
                    f"spectral_geometry harmonic_mode {idx} for operator {name!r} is not unit-normalized"
                )
            # Av = λ v check.
            result: list[Fraction] = []
            for row in mat_frac:
                total = sum(a * b for a, b in zip(row, v))
                result.append(total)
            expected = [lam * component for component in v]
            if result != expected:
                raise LawValidationError(
                    f"spectral_geometry Av=λv check failed for operator {name!r}, mode index {idx}"
                )


def validate_shuffle_equivalence_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for shuffle_equivalence_evidence.

    The permutations must be bijections over indices 0..n-1 for some n,
    without duplicates. Status must agree with the presence or absence of
    a counterexample.
    """
    permutations = payload.get("permutations")
    if not isinstance(permutations, list) or not permutations:
        raise LawValidationError("shuffle_equivalence_evidence.permutations must be a non-empty list")
    # All permutations must be lists of equal length and bijections over 0..n-1.
    first = permutations[0]
    if not isinstance(first, list) or not first:
        raise LawValidationError("shuffle_equivalence_evidence.permutations[0] must be a non-empty list")
    n = len(first)
    index_universe = list(range(n))
    unique_perms: set[tuple[int, ...]] = set()
    for perm in permutations:
        if not isinstance(perm, list) or len(perm) != n:
            raise LawValidationError("all permutations must be lists with uniform length")
        if sorted(perm) != index_universe:
            raise LawValidationError("each permutation must be a bijection over indices 0..n-1")
        tup = tuple(perm)
        if tup in unique_perms:
            raise LawValidationError("permutations must not contain duplicates")
        unique_perms.add(tup)
    status = payload.get("status")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass":
        if has_counterexample:
            raise LawValidationError("shuffle_equivalence_evidence with status 'pass' must not include a counterexample")
    elif status == "fail":
        if not has_counterexample:
            raise LawValidationError("shuffle_equivalence_evidence with status 'fail' must include a counterexample")
    else:
        raise LawValidationError("shuffle_equivalence_evidence.status must be 'pass' or 'fail'")


def validate_observation_equivalence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for observation_equivalence carriers.

    The carrier must encode a complete equivalence relation on the given
    observation_ids, either via explicit equivalence_classes or via a
    relation_table listing all related pairs, together with a total
    equivalence_table mapping each observation_id to the canonical
    representative of its equivalence class.

    Classes/relations must be total on observation_ids (no missing
    elements) and disjoint. The equivalence_table must:
    - have exactly the observation_ids as keys,
    - map into observation_ids,
    - be idempotent on representatives (table[rep] == rep),
    - induce the same partition of observation_ids as the
      equivalence_classes / relation_table when those are present.
    """
    observation_ids = payload.get("observation_ids")
    if not isinstance(observation_ids, list) or not observation_ids:
        raise LawValidationError("observation_equivalence.observation_ids must be a non-empty list")
    obs_ids = list(observation_ids)
    obs_set = set(obs_ids)
    if len(obs_set) != len(observation_ids):
        raise LawValidationError("observation_equivalence.observation_ids must be unique")

    classes = payload.get("equivalence_classes")
    relation_table = payload.get("relation_table")
    equivalence_table = payload.get("equivalence_table")
    if equivalence_table is None:
        raise LawValidationError(
            "observation_equivalence must provide an equivalence_table mapping "
            "each observation_id to a canonical representative"
        )

    if not classes and not relation_table:
        raise LawValidationError(
            "observation_equivalence must provide equivalence_classes or relation_table"
        )

    # Canonical partition induced by equivalence_classes / relation_table.
    canonical_from_relation: list[list[str]] | None = None

    # Class-based representation: each observation must appear in exactly one class.
    if classes:
        seen: set[str] = set()
        for cls in classes:
            if not isinstance(cls, list) or not cls:
                raise LawValidationError("equivalence_classes must be non-empty lists")
            for obs in cls:
                if obs not in obs_set:
                    raise LawValidationError(
                        f"equivalence_classes references unknown observation_id {obs!r}"
                    )
                if obs in seen:
                    raise LawValidationError(
                        f"observation_id {obs!r} appears in multiple equivalence_classes"
                    )
                seen.add(obs)
        if seen != obs_set:
            missing = obs_set - seen
            raise LawValidationError(
                f"equivalence_classes incomplete; missing observation_ids {sorted(missing)}"
            )
        canonical_from_relation = sorted(
            [sorted(cls) for cls in classes],
            key=lambda c: c[0],
        )

    # Relation-table representation: explicit equivalence relation on observation_ids.
    if relation_table:
        if not isinstance(relation_table, list) or not relation_table:
            raise LawValidationError("relation_table must be a non-empty list")
        pairs: set[tuple[str, str]] = set()
        for pair in relation_table:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not all(isinstance(x, str) for x in pair)
            ):
                raise LawValidationError("relation_table entries must be [obs_i, obs_j] pairs")
            a, b = pair
            if a not in obs_set or b not in obs_set:
                raise LawValidationError(
                    f"relation_table pair ({a!r}, {b!r}) references unknown observation_ids"
                )
            pairs.add((a, b))
        # Require explicit reflexivity.
        for obs in obs_set:
            if (obs, obs) not in pairs:
                raise LawValidationError(
                    f"relation_table must contain reflexive pair ({obs!r}, {obs!r})"
                )
        # Require symmetry: if (a,b) then (b,a).
        for a, b in list(pairs):
            if (b, a) not in pairs:
                raise LawValidationError(
                    f"relation_table must be symmetric; missing ({b!r}, {a!r}) for ({a!r}, {b!r})"
                )
        # Require transitivity: if (a,b) and (b,c) then (a,c).
        for a in obs_set:
            for b in obs_set:
                if (a, b) not in pairs:
                    continue
                for c in obs_set:
                    if (b, c) in pairs and (a, c) not in pairs:
                        raise LawValidationError(
                            f"relation_table must be transitive; missing ({a!r}, {c!r}) "
                            f"for ({a!r}, {b!r}) and ({b!r}, {c!r})"
                        )

        # Build canonical classes from the relation_table via connected components.
        adjacency: dict[str, set[str]] = {obs: set() for obs in obs_ids}
        for a, b in pairs:
            adjacency[a].add(b)
            adjacency[b].add(a)
        visited: set[str] = set()
        components: list[list[str]] = []
        for root in sorted(obs_ids):
            if root in visited:
                continue
            stack = [root]
            component: set[str] = set()
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                stack.extend(adjacency[current] - visited)
            components.append(sorted(component))
        components.sort(key=lambda c: c[0])
        if canonical_from_relation is None:
            canonical_from_relation = components
        elif canonical_from_relation != components:
            raise LawValidationError(
                "equivalence_classes and relation_table induce different partitions "
                "of observation_ids"
            )

    # Validate the equivalence_table as a canonical representative map.
    if not isinstance(equivalence_table, Mapping):
        raise LawValidationError("equivalence_table must be a mapping from observation_ids to representatives")
    table_keys = set(equivalence_table.keys())
    if table_keys != obs_set:
        missing = obs_set - table_keys
        extra = table_keys - obs_set
        parts: list[str] = []
        if missing:
            parts.append(f"missing keys {sorted(missing)}")
        if extra:
            parts.append(f"unexpected keys {sorted(extra)}")
        raise LawValidationError(
            "equivalence_table keys must match observation_ids exactly: " + "; ".join(parts)
        )
    for src, tgt in equivalence_table.items():
        if tgt not in obs_set:
            raise LawValidationError(
                f"equivalence_table maps {src!r} to unknown observation_id {tgt!r}"
            )
    # Idempotence on representatives: canonical elements must be fixed points.
    for element, representative in equivalence_table.items():
        rep_image = equivalence_table.get(representative)
        if rep_image != representative:
            raise LawValidationError(
                "equivalence_table must be idempotent on representatives "
                f"(table[{representative!r}] != {representative!r})"
            )

    # Partition induced by the equivalence_table.
    partition_by_rep: dict[str, list[str]] = {}
    for element, representative in equivalence_table.items():
        partition_by_rep.setdefault(representative, []).append(element)
    table_partition: list[list[str]] = [
        sorted(members) for members in partition_by_rep.values()
    ]
    table_partition.sort(key=lambda c: c[0])

    if canonical_from_relation is not None and table_partition != canonical_from_relation:
        raise LawValidationError(
            "equivalence_table classes do not match those induced by "
            "equivalence_classes / relation_table"
        )


def validate_observation_equivalence_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce basic consistency for observation_equivalence_evidence carriers.

    Evidence must reference an observation_equivalence carrier, provide
    evaluation and normalization witnesses, and declare a status aligned
    with the presence or absence of witness data.
    """
    equivalence_id = payload.get("equivalence_id")
    if not isinstance(equivalence_id, str):
        raise LawValidationError("observation_equivalence_evidence.equivalence_id must be a string")
    evaluation_witnesses = payload.get("evaluation_witnesses")
    normalization_witnesses = payload.get("normalization_witnesses")
    if not isinstance(evaluation_witnesses, Mapping) or not evaluation_witnesses:
        raise LawValidationError(
            "observation_equivalence_evidence.evaluation_witnesses must be a non-empty mapping"
        )
    if not isinstance(normalization_witnesses, Mapping) or not normalization_witnesses:
        raise LawValidationError(
            "observation_equivalence_evidence.normalization_witnesses must be a non-empty mapping"
        )
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("observation_equivalence_evidence.status must be 'pass' or 'fail'")


def _validate_equivalence_from_classes_and_relation(
    element_ids: list[str],
    classes: list[list[str]] | None,
    relation_table: list[list[str]] | None,
    element_label: str,
) -> None:
    """
    Shared helper for evaluation-equivalence-style relations.

    Enforces that equivalence_classes and/or relation_table encode a total
    equivalence relation on ``element_ids``.
    """
    ids_set = set(element_ids)
    if len(ids_set) != len(element_ids):
        raise LawValidationError(f"{element_label}_ids must be unique")
    canonical_from_relation: list[list[str]] | None = None

    if classes:
        seen: set[str] = set()
        for cls in classes:
            if not isinstance(cls, list) or not cls:
                raise LawValidationError("equivalence_classes must be non-empty lists")
            for elt in cls:
                if elt not in ids_set:
                    raise LawValidationError(
                        f"equivalence_classes references unknown {element_label}_id {elt!r}"
                    )
                if elt in seen:
                    raise LawValidationError(
                        f"{element_label}_id {elt!r} appears in multiple equivalence_classes"
                    )
                seen.add(elt)
        if seen != ids_set:
            missing = ids_set - seen
            raise LawValidationError(
                f"equivalence_classes incomplete; missing {element_label}_ids {sorted(missing)}"
            )
        canonical_from_relation = sorted(
            [sorted(cls) for cls in classes],
            key=lambda c: c[0],
        )

    if relation_table:
        if not isinstance(relation_table, list) or not relation_table:
            raise LawValidationError("relation_table must be a non-empty list")
        pairs: set[tuple[str, str]] = set()
        for pair in relation_table:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not all(isinstance(x, str) for x in pair)
            ):
                raise LawValidationError("relation_table entries must be [a, b] pairs")
            a, b = pair
            if a not in ids_set or b not in ids_set:
                raise LawValidationError(
                    f"relation_table pair ({a!r}, {b!r}) references unknown ids"
                )
            pairs.add((a, b))
        for elt in ids_set:
            if (elt, elt) not in pairs:
                raise LawValidationError(
                    f"relation_table must contain reflexive pair ({elt!r}, {elt!r})"
                )
        for a, b in list(pairs):
            if (b, a) not in pairs:
                raise LawValidationError("relation_table must be symmetric")
        for x in ids_set:
            for y in ids_set:
                if (x, y) not in pairs:
                    continue
                for z in ids_set:
                    if (y, z) in pairs and (x, z) not in pairs:
                        raise LawValidationError("relation_table must be transitive")

        if canonical_from_relation is not None:
            adjacency: dict[str, set[str]] = {elt: set() for elt in ids_set}
            for a, b in pairs:
                adjacency[a].add(b)
                adjacency[b].add(a)
            visited: set[str] = set()
            components: list[list[str]] = []
            for root in sorted(ids_set):
                if root in visited:
                    continue
                stack = [root]
                component: set[str] = set()
                while stack:
                    current = stack.pop()
                    if current in visited:
                        continue
                    visited.add(current)
                    component.add(current)
                    stack.extend(adjacency[current] - visited)
                components.append(sorted(component))
            components.sort(key=lambda c: c[0])
            if components != canonical_from_relation:
                raise LawValidationError(
                    "relation_table and equivalence_classes induce different partitions"
                )


def validate_evaluation_equivalence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for evaluation_equivalence carriers.

    The carrier must encode a complete equivalence relation on the given
    input_ids via equivalence_classes and/or relation_table, and must
    record a non-empty set of witness_ids.
    """
    input_ids = payload.get("input_ids")
    if not isinstance(input_ids, list) or not input_ids:
        raise LawValidationError("evaluation_equivalence.input_ids must be a non-empty list")
    classes = payload.get("equivalence_classes")
    relation_table = payload.get("relation_table")
    if not classes and not relation_table:
        raise LawValidationError(
            "evaluation_equivalence must provide equivalence_classes or relation_table"
        )
    _validate_equivalence_from_classes_and_relation(
        list(input_ids), classes or None, relation_table or None, "input"
    )
    witness_ids = payload.get("witness_ids")
    if not isinstance(witness_ids, list) or not witness_ids:
        raise LawValidationError("evaluation_equivalence.witness_ids must be a non-empty list")


def validate_judgment_equivalence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for judgment_equivalence carriers.

    The carrier must encode a complete equivalence relation on the given
    judgment_ids via equivalence_classes and/or relation_table, with a
    non-empty witness_ids array.
    """
    judgment_ids = payload.get("judgment_ids")
    if not isinstance(judgment_ids, list) or not judgment_ids:
        raise LawValidationError("judgment_equivalence.judgment_ids must be a non-empty list")
    classes = payload.get("equivalence_classes")
    relation_table = payload.get("relation_table")
    if not classes and not relation_table:
        raise LawValidationError(
            "judgment_equivalence must provide equivalence_classes or relation_table"
        )
    _validate_equivalence_from_classes_and_relation(
        list(judgment_ids), classes or None, relation_table or None, "judgment"
    )
    witness_ids = payload.get("witness_ids")
    if not isinstance(witness_ids, list) or not witness_ids:
        raise LawValidationError("judgment_equivalence.witness_ids must be a non-empty list")


def validate_evaluation_equivalence_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for evaluation_equivalence_evidence.

    Requires non-empty input_ids, widened_ids, witness_ids, and a status
    aligned with the presence or absence of a counterexample.
    """
    input_ids = payload.get("input_ids")
    widened_ids = payload.get("widened_ids")
    witness_ids = payload.get("witness_ids")
    if not isinstance(input_ids, list) or not input_ids:
        raise LawValidationError("evaluation_equivalence_evidence.input_ids must be a non-empty list")
    if not isinstance(widened_ids, list) or not widened_ids:
        raise LawValidationError("evaluation_equivalence_evidence.widened_ids must be a non-empty list")
    if not isinstance(witness_ids, list) or not witness_ids:
        raise LawValidationError("evaluation_equivalence_evidence.witness_ids must be a non-empty list")
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("evaluation_equivalence_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "evaluation_equivalence_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "evaluation_equivalence_evidence with status 'fail' must include a counterexample"
        )


def validate_substitution_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for substitution_evidence.

    Status must be 'pass' or 'fail'; a counterexample is required when
    status == 'fail' and must be absent when status == 'pass'.
    """
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("substitution_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "substitution_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "substitution_evidence with status 'fail' must include a counterexample"
        )


def validate_evaluation_context(payload: Mapping[str, Any]) -> None:
    """
    Enforce basic framing laws for evaluation_context:
    - frames must be non-empty,
    - frame_ordering must enumerate 0..len(frames)-1.
    """
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise LawValidationError("evaluation_context.frames must be a non-empty list")
    ordering = payload.get("frame_ordering")
    if not isinstance(ordering, list):
        raise LawValidationError("evaluation_context.frame_ordering must be a list")
    if ordering != list(range(len(frames))):
        raise LawValidationError("evaluation_context.frame_ordering must be 0..len(frames)-1")


def validate_reducible_environment(payload: Mapping[str, Any]) -> None:
    """
    Enforce basic shape constraints for reducible_environment.
    """
    bindings = payload.get("bindings")
    if not isinstance(bindings, Mapping) or not bindings:
        raise LawValidationError("reducible_environment.bindings must be a non-empty mapping")


def validate_fixed_profile_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for fixed_profile_evidence.

    Status must be 'pass' or 'fail'; a counterexample is required when
    status == 'fail' and must be absent when status == 'pass'.
    """
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("fixed_profile_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "fixed_profile_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "fixed_profile_evidence with status 'fail' must include a counterexample"
        )


def validate_presheaf_site(payload: Mapping[str, Any]) -> None:
    """
    Enforce basic category and cover laws for a presheaf_site.
    """
    objects = payload.get("objects") or []
    arrows = payload.get("arrows") or []
    obj_set = set(objects)
    arrow_set = set(arrows)
    identity = payload.get("identity") or {}
    composition = payload.get("composition") or {}
    covers = payload.get("covers") or []
    # Identity: one arrow per object, all within arrows set.
    if set(identity.keys()) != obj_set:
        raise LawValidationError("presheaf_site.identity must provide an identity arrow for every object")
    for obj, arr in identity.items():
        if obj not in obj_set:
            raise LawValidationError(f"presheaf_site.identity key {obj!r} not in objects")
        if arr not in arrow_set:
            raise LawValidationError(f"presheaf_site.identity[{obj!r}] = {arr!r} not in arrows")
    # Composition keys and values must be arrows; keys encode pairs \"g|f\".
    for key, value in composition.items():
        if value not in arrow_set:
            raise LawValidationError(f"presheaf_site.composition[{key!r}] = {value!r} not in arrows")
        parts = key.split("|")
        if len(parts) != 2:
            raise LawValidationError("presheaf_site.composition keys must encode pairs as 'g|f'")
        g, f = parts
        if g not in arrow_set or f not in arrow_set:
            raise LawValidationError(f"presheaf_site.composition pair ({g!r},{f!r}) references unknown arrows")
    # Covers: each cover.object in objects; each cover arrow in arrows.
    for cover in covers:
        obj = cover.get("object")
        arrs = cover.get("arrows") or []
        if obj not in obj_set:
            raise LawValidationError(f"presheaf_site cover references unknown object {obj!r}")
        for arr in arrs:
            if arr not in arrow_set:
                raise LawValidationError(f"presheaf_site cover for {obj!r} references unknown arrow {arr!r}")


def validate_presheaf(payload: Mapping[str, Any]) -> None:
    """
    Enforce shape and basic functoriality laws for a presheaf carrier.
    """
    objects = payload.get("objects") or []
    arrows = payload.get("arrows") or []
    obj_set = set(objects)
    arrow_set = set(arrows)
    sections = payload.get("sections") or {}
    restrictions = payload.get("restrictions") or {}
    covers = payload.get("covers") or []
    commutation_checks = payload.get("commutation_checks") or {}
    # Sections: object-indexed; all objects known.
    for obj, secs in sections.items():
        if obj not in obj_set:
            raise LawValidationError(f"presheaf.sections references unknown object {obj!r}")
        if not isinstance(secs, list):
            raise LawValidationError("presheaf.sections entries must be lists")
    # Restrictions: arrow-indexed maps with domain/codomain in objects.
    for arr, data in restrictions.items():
        if arr not in arrow_set:
            raise LawValidationError(f"presheaf.restrictions references unknown arrow {arr!r}")
        src = data.get("from")
        tgt = data.get("to")
        if src not in obj_set or tgt not in obj_set:
            raise LawValidationError("presheaf.restrictions entries must use known objects in 'from'/'to'")
        sec_src = sections.get(src, [])
        sec_tgt = sections.get(tgt, [])
        mapping = data.get("map") or {}
        # Totality on domain: each section at src must map into sections at tgt.
        for s in sec_src:
            if s not in mapping:
                raise LawValidationError(f"restriction for arrow {arr!r} missing image for section {s!r}")
        for s_src, s_tgt in mapping.items():
            if s_src not in sec_src:
                raise LawValidationError(f"restriction for arrow {arr!r} has domain section {s_src!r} not in sections[{src!r}]")
            if s_tgt not in sec_tgt:
                raise LawValidationError(f"restriction for arrow {arr!r} maps to section {s_tgt!r} not in sections[{tgt!r}]")
    # Covers: mirror presheaf_site shape; ensure referenced objects/arrows exist.
    for cover in covers:
        obj = cover.get("object")
        arrs = cover.get("arrows") or []
        if obj not in obj_set:
            raise LawValidationError(f"presheaf cover references unknown object {obj!r}")
        for arr in arrs:
            if arr not in arrow_set:
                raise LawValidationError(f"presheaf cover for {obj!r} references unknown arrow {arr!r}")
    # Commutation checks: when present, must be a mapping with boolean
    # values; all recorded laws must hold. The mapping may be empty to
    # accommodate diagnostic presheaves used to witness law failures.
    if not isinstance(commutation_checks, Mapping):
        raise LawValidationError("presheaf.commutation_checks must be a mapping")
    for law, ok in commutation_checks.items():
        if not isinstance(ok, bool):
            raise LawValidationError("presheaf.commutation_checks values must be booleans")
        if not ok:
            raise LawValidationError(
                f"presheaf law {law!r} reported as failing in commutation_checks"
            )


def validate_sheafification_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for sheafification_evidence.

    Status must agree with the presence or absence of a counterexample.
    """
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("sheafification_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "sheafification_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "sheafification_evidence with status 'fail' must include a counterexample"
        )


def validate_sheaf(payload: Mapping[str, Any]) -> None:
    """
    Enforce basic coherence for sheaf carriers: covers must align with
    gluing_families and glued_sections.
    """
    covers = payload.get("covers") or []
    cover_ids: list[str] = []
    for cover in covers:
        cid = cover.get("cover_id")
        if not isinstance(cid, str):
            raise LawValidationError("sheaf.covers entries must provide string cover_id")
        cover_ids.append(cid)
    cover_set = set(cover_ids)
    gluing = payload.get("gluing_families") or []
    glued = payload.get("glued_sections") or {}
    # Each gluing family must reference a known cover_id.
    for fam in gluing:
        cid = fam.get("cover_id")
        if cid not in cover_set:
            raise LawValidationError(f"sheaf.gluing_families references unknown cover_id {cid!r}")
    # glued_sections keys must be subset of cover_ids.
    for cid in glued.keys():
        if cid not in cover_set:
            raise LawValidationError(f"sheaf.glued_sections references unknown cover_id {cid!r}")


def validate_context_geometry(payload: Mapping[str, Any]) -> None:
    """
    Minimal shape check for context_geometry.
    """
    site_id = payload.get("site_id")
    if not isinstance(site_id, str):
        raise LawValidationError("context_geometry.site_id must be a string")


def validate_sheaf_profile_consistency_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for sheaf_profile_consistency_evidence.
    """
    sheaf_id = payload.get("sheaf_id")
    presheaf_id = payload.get("presheaf_id")
    if not isinstance(sheaf_id, str) and not isinstance(presheaf_id, str):
        raise LawValidationError(
            "sheaf_profile_consistency_evidence must provide sheaf_id or presheaf_id"
        )
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("sheaf_profile_consistency_evidence.status must be 'pass' or 'fail'")
    checks = payload.get("checks")
    if not isinstance(checks, Mapping) or not checks:
        raise LawValidationError("sheaf_profile_consistency_evidence.checks must be a non-empty mapping")


def validate_measured_observation_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for measured_observation_evidence.

    Status must be 'pass' or 'fail'; a counterexample is required when
    status == 'fail' and must be absent when status == 'pass'.
    """
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("measured_observation_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "measured_observation_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "measured_observation_evidence with status 'fail' must include a counterexample"
        )


def validate_normalized_observation_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for normalized_observation_evidence.

    The evidence must reference an observation, record the iteration count
    used during normalization, and declare a status aligned with the
    presence or absence of a counterexample.
    """
    observation_id = payload.get("observation_id")
    if not isinstance(observation_id, str):
        raise LawValidationError("normalized_observation_evidence.observation_id must be a string")
    iteration_count = payload.get("iteration_count")
    if not isinstance(iteration_count, int) or iteration_count < 0:
        raise LawValidationError("normalized_observation_evidence.iteration_count must be a non-negative integer")
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("normalized_observation_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "normalized_observation_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "normalized_observation_evidence with status 'fail' must include a counterexample"
        )


def validate_stabilized_observation_evidence(payload: Mapping[str, Any]) -> None:
    """
    Enforce internal consistency for stabilized_observation_evidence.

    The evidence must reference an observation, record equivalence witnesses,
    and declare a status aligned with the presence or absence of a
    counterexample.
    """
    observation_id = payload.get("observation_id")
    if not isinstance(observation_id, str):
        raise LawValidationError("stabilized_observation_evidence.observation_id must be a string")
    witnesses = payload.get("equivalence_witnesses")
    if not isinstance(witnesses, Mapping) or not witnesses:
        raise LawValidationError(
            "stabilized_observation_evidence.equivalence_witnesses must be a non-empty mapping"
        )
    status = payload.get("status")
    if status not in {"pass", "fail"}:
        raise LawValidationError("stabilized_observation_evidence.status must be 'pass' or 'fail'")
    has_counterexample = "counterexample" in payload and payload["counterexample"] is not None
    if status == "pass" and has_counterexample:
        raise LawValidationError(
            "stabilized_observation_evidence with status 'pass' must not include a counterexample"
        )
    if status == "fail" and not has_counterexample:
        raise LawValidationError(
            "stabilized_observation_evidence with status 'fail' must include a counterexample"
        )
