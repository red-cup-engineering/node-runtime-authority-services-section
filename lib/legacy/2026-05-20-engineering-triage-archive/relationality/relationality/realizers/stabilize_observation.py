from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.observation_equivalence_utils import (
    canonicalize_observation_element,
    find_observation_equivalence,
)
from relationality.observation_utils import record_observation
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    stabilize_observation realizer.

    Input
    -----
    observation:
        Normalized Observation carrier (kind ``observation``).
    trace:
        Trace carrier whose recent elements witness long-run stability.

    Semantics
    ---------
    Realizes the StabilizeObservation act as a closure check: given an
    observation that is expected to be normalized with respect to the
    ambient observation-equivalence relation, ensure that its element is
    already the canonical representative of its equivalence class.

    - When an observation_equivalence carrier exists whose observation_ids
      contain the observation element, stabilize_observation verifies that
      the element is equal to the canonical representative; otherwise it
      raises a LawValidationError.
    - When no such carrier is present, the observation is left unchanged;
      this corresponds to the (temporary) case where no observation
      equivalence has yet been established for this element.
    """
    normalized = inputs.get("observation")
    trace = inputs.get("trace")
    if normalized is None or trace is None:
        raise KeyError("stabilize_observation requires 'observation' and 'trace' inputs")
    if normalized.get("kind") != "observation":
        raise LawValidationError("stabilize_observation observation input must have kind 'observation'")
    if trace.get("kind") != "trace":
        raise LawValidationError("stabilize_observation trace input must have kind 'trace'")

    validate_trace(trace)

    element = normalized.get("element")
    if not isinstance(element, str):
        raise LawValidationError("stabilize_observation requires observation.element to be a string")

    eq = find_observation_equivalence(graph, element)
    if eq is None:
        raise LawValidationError(
            "stabilize_observation requires an observation_equivalence carrier for the observation element"
        )

    canonical_element, _ = canonicalize_observation_element(eq, element)
    if canonical_element != element:
        raise LawValidationError(
            "stabilize_observation requires input observation to be normalized "
            "to the canonical representative of its equivalence class"
        )

    # Long-run stability: measure how many recent trace elements collapse to
    # the same canonical representative under the observation equivalence.
    window_size = 3
    elements: List[str] = list(trace.get("elements", []))
    if not elements:
        raise LawValidationError("stabilize_observation requires a non-empty trace")
    table = eq.get("equivalence_table", {})
    stable_run_length = 0
    for state in elements[: min(window_size, len(elements))]:
        rep = table.get(state)
        if rep is None:
            raise LawValidationError(
                "stabilize_observation trace element not present in observation_equivalence.equivalence_table"
            )
        if rep != canonical_element:
            break
        stable_run_length += 1
    if stable_run_length == 0:
        raise LawValidationError(
            "stabilize_observation requires the most recent trace element to "
            "lie in the same observation-equivalence class as the observation element"
        )

    stabilized = record_observation(
        carrier_id=normalized["carrier_id"],
        measurement_frame_id=normalized["measurement_frame_id"],
        element=normalized["element"],
        act_ref="StabilizeObservation",
    )

    # Evidence that the observation is stable under the equivalence closure.
    witnesses = {
        "equivalence_id": eq["id"],
        "representative": canonical_element,
        "trace_id": trace["id"],
        "window_size": window_size,
        "stable_run_length": stable_run_length,
    }
    evidence = {
        "kind": "stabilized_observation_evidence",
        "observation_id": stabilized["id"],
        "equivalence_witnesses": witnesses,
        "status": "pass",
        "act_ref": "StabilizeObservation",
    }
    ensure_id_coherence(evidence)

    edge_observation = {
        "operator": "stabilize_observation",
        "src": normalized["id"],
        "tgt": stabilized["id"],
    }
    edge_evidence = {
        "operator": "stabilize_observation",
        "src": stabilized["id"],
        "tgt": evidence["id"],
    }
    edge_trace = {
        "operator": "stabilize_observation",
        "src": trace["id"],
        "tgt": evidence["id"],
    }
    edge_equivalence = {
        "operator": "stabilize_observation",
        "src": eq["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[stabilized, evidence],
        edges=[edge_observation, edge_evidence, edge_trace, edge_equivalence],
        bindings={"observation": stabilized["id"]},
    )
