from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.observation_equivalence_utils import canonicalize_observation_element
from relationality.validation import LawValidationError, validate_trace, validate_observation_equivalence


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    trace_observation_equivalence realizer.

    Inputs
    ------
    trace:
        Trace carrier whose elements are observations in the ambient lattice.
    observation_equivalence:
        ObservationEquivalence carrier providing NormalizeObservationEquivalence.

    Semantics
    ---------
    Realizes TraceObservationEquivalence = (CompleteTrace NormalizeObservationEquivalence)
    by threading the observation equivalence along the completed trace and
    emitting a trace_observation_equivalence carrier. Each trace element is
    mapped to its canonical representative via NormalizeObservationEquivalence.
    """
    trace = inputs.get("trace")
    observation_equivalence = inputs.get("observation_equivalence")
    if trace is None or observation_equivalence is None:
        raise KeyError("trace_observation_equivalence requires 'trace' and 'observation_equivalence' inputs")
    if trace.get("kind") != "trace":
        raise LawValidationError("trace_observation_equivalence 'trace' input must have kind 'trace'")
    if observation_equivalence.get("kind") != "observation_equivalence":
        raise LawValidationError(
            "trace_observation_equivalence 'observation_equivalence' input must have kind 'observation_equivalence'"
        )

    validate_trace(trace)
    validate_observation_equivalence(observation_equivalence)

    elements: List[str] = list(trace.get("elements", []))
    step_equivalences: List[dict] = []
    for elt in elements:
        rep, _ = canonicalize_observation_element(observation_equivalence, elt)
        step_equivalences.append({"element": elt, "representative": rep})

    toe = {
        "kind": "trace_observation_equivalence",
        "trace_id": trace["id"],
        "observation_equivalence_id": observation_equivalence["id"],
        "step_equivalences": step_equivalences,
        "act_ref": "TraceObservationEquivalence",
    }
    ensure_id_coherence(toe)

    edge = {
        "operator": "trace_observation_equivalence",
        "src": trace["id"],
        "tgt": toe["id"],
    }

    return RealizerOutput(
        nodes=[toe],
        edges=[edge],
        bindings={"trace_observation_equivalence": toe["id"]},
    )

