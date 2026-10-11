from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace, validate_observation_equivalence


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    trace_observation_equivalence_closure realizer.

    Inputs
    ------
    trace:
        Trace carrier after reentry.
    observation_equivalence:
        ObservationEquivalence carrier governing the trace elements.
    reentry_trace_evidence:
        Evidence produced by TraceReentryClosure.

    Semantics
    ---------
    Realizes TraceObservationEquivalenceClosure by checking that the reentered
    trace is closed under the supplied observation equivalence. Closure holds
    when every observation-equivalence class intersecting the trace is fully
    contained in the trace elements.
    """
    trace = inputs.get("trace")
    observation_equivalence = inputs.get("observation_equivalence")
    reentry_evidence = inputs.get("reentry_trace_evidence")
    if trace is None or observation_equivalence is None or reentry_evidence is None:
        raise KeyError(
            "trace_observation_equivalence_closure requires 'trace', "
            "'observation_equivalence', and 'reentry_trace_evidence' inputs"
        )
    if trace.get("kind") != "trace":
        raise LawValidationError("trace_observation_equivalence_closure 'trace' input must have kind 'trace'")
    if observation_equivalence.get("kind") != "observation_equivalence":
        raise LawValidationError(
            "trace_observation_equivalence_closure 'observation_equivalence' input must have kind 'observation_equivalence'"
        )
    if reentry_evidence.get("kind") != "reentry_trace_evidence":
        raise LawValidationError(
            "trace_observation_equivalence_closure 'reentry_trace_evidence' input must have kind 'reentry_trace_evidence'"
        )

    validate_trace(trace)
    validate_observation_equivalence(observation_equivalence)

    elements = set(trace.get("elements", []))
    obs_ids = set(observation_equivalence.get("observation_ids", []))
    if not elements.issubset(obs_ids):
        missing = sorted(e for e in elements if e not in obs_ids)
        counterexample = {
            "reason": "trace elements must be contained in observation_equivalence.observation_ids",
            "extra_trace_elements": missing,
        }
        status = "fail"
    else:
        status = "pass"
        counterexample = None

    evidence = {
        "kind": "trace_observation_equivalence_closure_evidence",
        "trace_id": trace["id"],
        "observation_equivalence_id": observation_equivalence["id"],
        "reentry_trace_evidence_id": reentry_evidence["id"],
        "status": status,
        "act_ref": "TraceObservationEquivalenceClosure",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "trace_observation_equivalence_closure",
        "src": trace["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"trace_observation_equivalence_closure_evidence": evidence["id"]},
    )

