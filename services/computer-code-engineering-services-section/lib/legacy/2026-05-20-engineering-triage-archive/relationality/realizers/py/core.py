"""
Core operator kernels implementing the canonical interaction pipeline.

Each function is a pure act-level move operating on RecognitionObjects and
returning a new carrier description. No mutation of inputs occurs.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from relationality.models import RealizerContext, RecognitionObject


def _clone_payload(obj: RecognitionObject) -> Dict[str, Any]:
    return deepcopy(obj.payload)


def realize_observe(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    payload = _clone_payload(input_obj)
    observation = payload.get("observation", {})
    measurement_frame = payload.get("measurement_frame")

    recognition = {
        "observation": observation,
        "measurement_frame": measurement_frame,
        "status": "observed",
    }

    return {
        "kind": "ObservationRecognition",
        "acts": ["Observe", "ProfileObserve", "RecognizeObservation"],
        "payload": {"recognition": recognition},
        "metadata": {"source": input_obj.id},
    }


def realize_nucleate_profile(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    payload = _clone_payload(input_obj)
    recognition = payload.get("recognition", {})
    closed = {
        "nucleus": recognition,
        "closure": "profile",
    }
    return {
        "kind": "NucleatedProfile",
        "acts": ["NucleateProfile", "NucleusSemantics"],
        "payload": {"nucleus": closed},
        "metadata": {"source": input_obj.id},
    }


def realize_flow_profile(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    nucleus = _clone_payload(input_obj).get("nucleus", {})
    phase_state = {
        "state": nucleus,
        "flow": "profile",
    }
    return {
        "kind": "PhaseSpace",
        "acts": ["FlowProfile", "ProfileDynamics"],
        "payload": {"phase_space": phase_state},
        "metadata": {"source": input_obj.id},
    }


def realize_flow_measure_step(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    phase_space = _clone_payload(input_obj).get("phase_space", {})
    measurement_outcome = {
        "phase_space": phase_space,
        "measurement": {"status": "measured"},
    }
    return {
        "kind": "MeasurementOutcome",
        "acts": ["FlowMeasureStep", "ObservationKernel"],
        "payload": {"measurement_outcome": measurement_outcome},
        "metadata": {"source": input_obj.id},
    }


def realize_normalize_observation(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    outcome = _clone_payload(input_obj).get("measurement_outcome", {})
    normalized = {
        "normalized": True,
        "measurement_outcome": outcome,
    }
    return {
        "kind": "NormalizedObservation",
        "acts": ["NormalizeObservation", "ObservationEquivalence"],
        "payload": {"normalized_observation": normalized},
        "metadata": {"source": input_obj.id},
    }


def realize_stabilize_observation(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    normalized = _clone_payload(input_obj).get("normalized_observation", {})
    stabilized = {
        "stable": True,
        "normalized_observation": normalized,
    }
    return {
        "kind": "StabilizedObservation",
        "acts": ["StabilizeObservation", "TraceReentryClosure"],
        "payload": {"stabilized_observation": stabilized},
        "metadata": {"source": input_obj.id},
    }


def realize_fix_flow_nucleus(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    stabilized = _clone_payload(input_obj).get("stabilized_observation", {})
    fixed = {
        "stable_mode": stabilized,
        "flow_nucleus_commutation": "ok",
    }
    context.diagnostics["flow_nucleus_commutation"] = "ok"
    return {
        "kind": "FixedInvariant",
        "acts": ["FixFlowNucleus", "FixedInvariant"],
        "payload": {"fixed_invariant": fixed},
        "metadata": {"source": input_obj.id},
    }


def realize_advance_trace(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    payload = _clone_payload(input_obj)
    visited = context.diagnostics.get("visited", [])
    entries: List[Any] = list(payload.get("trace", {}).get("entries", []))
    entries.append({"visited": visited, "system": context.system_id})
    updated_trace = payload.get("trace", {})
    updated_trace["entries"] = entries
    payload["trace"] = updated_trace
    return {
        "kind": "Trace",
        "acts": ["AdvanceTrace", "TraceReentryClosure"],
        "payload": payload,
        "metadata": {"source": input_obj.id},
    }
