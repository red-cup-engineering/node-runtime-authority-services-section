"""Loaders for canonical carriers and runbooks."""

from __future__ import annotations

import json
import pathlib
from typing import Dict, Tuple

import yaml

from relationality.canonical import canonicalize_json, hash_without_keys
from relationality.errors import (
    DuplicateObjectError,
    HashMismatchError,
    IDMismatchError,
    KindMismatchError,
    LoaderError,
)
from relationality.schemas import validate_object, validate_runbook, load_schema
from relationality.realizers.judgment_laws import ensure_judgment_laws, has_judgment_tables
from relationality.realizer_registry import resolve_realizer
from relationality.realizers.flow_laws import flow_laws
from relationality.realizers.nucleus_laws import nucleus_laws
from relationality.realizers.commutation import commutation

# Operator signatures derived from realizers/runbooks in this repository.
# Each operator maps to a list of allowed (input_kinds, output_kinds) tuples.
OP_SIGNATURES = {
    "observe": [(["observation_carrier"], ["trace"]), (["observation_carrier", "trace"], ["trace"])],
    "nucleate_profile": [
        (["profile"], ["profile"]),
        (["observation_carrier", "profile"], ["profile"]),
        (["profile", "measurement_frame", "regime", "phase_space"], ["profile"]),
    ],
    "flow_profile": [
        (["profile"], ["profile"]),
        (["profile", "regime", "phase_space"], ["profile"]),
    ],
    "flow_measure_step": [
        (
            ["observation_carrier", "measurement_frame", "phase_space", "regime", "trace"],
            ["observation_carrier"],
        ),
        (
            ["observation_carrier", "measurement_frame", "phase_space", "regime", "trace"],
            ["observation_carrier", "observation_equivalence_evidence"],
        ),
    ],
    "normalize_observation": [
        (["observation_carrier", "measurement_frame"], ["observation_carrier"]),
        (["observation_carrier", "measurement_frame"], ["observation_carrier", "observation_equivalence_evidence"]),
        (["observation_carrier"], ["observation_carrier"]),
    ],
    "stabilize_observation": [
        (["observation_carrier", "measurement_frame"], ["observation_carrier"]),
        (["observation_carrier", "measurement_frame"], ["observation_carrier", "observation_equivalence_evidence"]),
        (["observation_carrier"], ["observation_carrier"]),
    ],
    "fix_flow_nucleus": [
        (
            ["profile", "phase_space", "regime", "trace"],
            [
                "fixed_invariants",
                "judgment_laws_evidence",
                "flow_laws_evidence",
                "nucleus_laws_evidence",
                "commutation_evidence",
                "trace_evidence",
            ],
        ),
        (["profile"], ["fixed_invariants"]),
    ],
    "fix_flow": [(["profile"], ["flow_laws_evidence"])],
    "fix_nucleus": [(["profile"], ["nucleus_laws_evidence"])],
    "commutation": [(["profile"], ["commutation_evidence"])],
    "judgment_laws": [(["profile"], ["judgment_laws_evidence"])],
    "flow_laws": [(["profile"], ["flow_laws_evidence"])],
    "nucleus_laws": [(["profile"], ["nucleus_laws_evidence"])],
    "trace_laws": [(["trace"], ["trace_evidence"])],
    "start_trace": [(["observation_carrier"], ["trace"])],
    "advance_trace": [(["trace", "observation_carrier"], ["trace"])],
    "stabilize_trace": [(["trace"], ["trace", "trace_evidence"])],
    "shuffle_trace": [(["trace"], ["trace", "shuffle_equivalence_evidence"])],
    "temporal_modality": [(["profile"], ["temporal_modality_evidence"])],
    "spectral_geometry": [(["fixed_invariants"], ["spectral_geometry"])],
    "normalize_judgment_equivalence": [
        (["judgment_equivalence"], ["judgment_equivalence", "judgment_equivalence_evidence"])
    ],
    "evaluate_judgment": [
        (["term_context"], ["judgment_equivalence", "judgment_equivalence_evidence"])
    ],
    "discipline_profile": [
        (
            ["profile", "trace_evidence", "judgment_equivalence_evidence"],
            ["fixed_invariants"],
        )
    ],
}


def _schema_name_for_kind(kind: str) -> str:
    """Map a kind name to its schema filename."""
    return f"{kind.replace('_', '-')}.schema.json"


def _load_json(path: pathlib.Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_yaml(path: pathlib.Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_object_file(path: pathlib.Path) -> Dict:
    """Load and validate a single object file."""
    parts = path.name.split(".")
    if len(parts) != 4 or parts[-2:] != ["object", "json"]:
        raise LoaderError(f"Invalid object filename format: {path.name}")
    expected_id, expected_kind = parts[0], parts[1]

    raw_payload = _load_json(path)
    if not isinstance(raw_payload, dict):
        raise LoaderError(f"Object payload must be a mapping: {path}")
    payload = json.loads(canonicalize_json(raw_payload).decode("utf-8"))
    # Hash against the canonical payload without the derived id to avoid
    # self-referential hashing; see README canonicalization rules.
    computed_hash = hash_without_keys(payload)
    if computed_hash != expected_id:
        raise HashMismatchError(
            f"Hash mismatch for {path}: expected {expected_id}, computed {computed_hash}"
        )
    embedded_id = payload.get("id")
    if embedded_id is None or embedded_id != computed_hash:
        raise IDMismatchError(
            f"Embedded id {embedded_id} does not match computed {computed_hash} in {path}"
        )
    embedded_kind = payload.get("kind")
    if embedded_kind != expected_kind:
        raise KindMismatchError(
            f"Kind mismatch: filename kind={expected_kind}, payload kind={embedded_kind}"
        )

    schema_name = _schema_name_for_kind(expected_kind)
    validate_object(payload, schema_name)
    if embedded_kind == "profile":
        ensure_judgment_laws(payload)
        # If flow/nucleus maps exist, enforce their laws and commutation.
        if payload.get("flow_map"):
            flow_laws(None, [payload], ctx={})
        if payload.get("nucleus_map"):
            nucleus_laws(None, [payload], ctx={})
        if payload.get("flow_map") and payload.get("nucleus_map"):
            commutation(None, [payload], ctx={})
    elif embedded_kind in {"phase_space", "fixed_invariants"} and has_judgment_tables(payload):
        ensure_judgment_laws(payload)
    return {"id": computed_hash, "kind": expected_kind, "payload": payload}


def load_objects(directory: pathlib.Path) -> Dict[str, Dict[Tuple[str, str], Dict]]:
    """Scan a directory for canonical objects and return indexes."""
    if not directory.exists():
        raise LoaderError(f"Objects directory does not exist: {directory}")

    by_id_kind: Dict[Tuple[str, str], Dict] = {}
    by_kind: Dict[str, Dict[str, Dict]] = {}

    for path in sorted(directory.glob("*.object.json")):
        loaded = load_object_file(path)
        key = (loaded["id"], loaded["kind"])
        if key in by_id_kind:
            raise DuplicateObjectError(f"Duplicate object for {key} at {path}")
        by_id_kind[key] = loaded["payload"]
        by_kind.setdefault(loaded["kind"], {})[loaded["id"]] = loaded["payload"]

    return {"by_id_kind": by_id_kind, "by_kind": by_kind}


def load_runbook_file(path: pathlib.Path) -> Dict:
    """Load and validate a single runbook file."""
    parts = path.name.split(".")
    if len(parts) != 3 or parts[1:] != ["runbook", "yaml"]:
        raise LoaderError(f"Invalid runbook filename format: {path.name}")
    expected_id = parts[0]

    raw_payload = _load_yaml(path)
    if not isinstance(raw_payload, dict):
        raise LoaderError(f"Runbook payload must be a mapping: {path}")
    payload = json.loads(canonicalize_json(raw_payload).decode("utf-8"))
    # Hash against payload sans id to avoid recursive dependence on the id field.
    computed_hash = hash_without_keys(payload)
    if computed_hash != expected_id:
        raise HashMismatchError(
            f"Hash mismatch for {path}: expected {expected_id}, computed {computed_hash}"
        )
    embedded_id = payload.get("id")
    if embedded_id is None or embedded_id != computed_hash:
        raise IDMismatchError(
            f"Embedded id {embedded_id} does not match computed {computed_hash} in {path}"
        )

    validate_runbook(payload)
    # Enforce step_index ordering and closed-world carrier kinds/operators.
    schema = load_schema("runbook.schema.yaml")
    allowed_ops = set(schema["properties"]["steps"]["items"]["properties"]["operator"]["enum"])
    for idx, step in enumerate(payload.get("steps", [])):
        step_index = step.get("step_index")
        if step_index is None or step_index != idx:
            raise LoaderError(f"Step index mismatch in {path}: expected {idx}, found {step_index}")
        op = step["operator"]
        if op not in allowed_ops:
            raise LoaderError(f"Unknown operator '{op}' in step {idx} of {path}")
        # Ensure a realizer module exists for the operator.
        try:
            resolve_realizer(op)
        except LoaderError as exc:
            raise LoaderError(f"Missing realizer for operator '{op}' in {path}") from exc
        for field in ("input_kinds", "output_kinds"):
            kinds = step.get(field)
            if not isinstance(kinds, list) or not kinds:
                raise LoaderError(f"{field} must be a non-empty list in step {idx} of {path}")
        if "input_ids" in step and len(step.get("input_ids", [])) != len(step.get("input_kinds", [])):
            raise LoaderError(
                f"input_ids length {len(step.get('input_ids', []))} does not match input_kinds "
                f"{len(step.get('input_kinds', []))} in step {idx} of {path}"
            )
        for field in ("input_kinds", "output_kinds"):
            for kind in step.get(field, []):
                schema_name = _schema_name_for_kind(kind)
                try:
                    load_schema(schema_name)
                except FileNotFoundError as exc:
                    raise LoaderError(f"Unknown kind '{kind}' in {field} of step {idx}") from exc
        # Operator-specific signature check when known.
        if op in OP_SIGNATURES:
            sigs = OP_SIGNATURES[op]
            candidate = (step.get("input_kinds", []), step.get("output_kinds", []))
            if candidate not in sigs:
                raise LoaderError(f"Step {idx} kinds {candidate} invalid for operator {op}")
    return {"id": computed_hash, "payload": payload}


def load_runbooks(directory: pathlib.Path) -> Dict[str, Dict]:
    """Scan a directory for runbooks and return an index keyed by id."""
    if not directory.exists():
        raise LoaderError(f"Runbooks directory does not exist: {directory}")

    runbooks: Dict[str, Dict] = {}
    for path in sorted(directory.glob("*.runbook.yaml")):
        loaded = load_runbook_file(path)
        if loaded["id"] in runbooks:
            raise DuplicateObjectError(f"Duplicate runbook id {loaded['id']} at {path}")
        runbooks[loaded["id"]] = loaded["payload"]
    return runbooks
