from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    trace_profile realizer.

    Inputs
    ------
    trace:
        Completed trace carrier whose elements are recognitions in a profile.
    profile_topos:
        ProfileTopos carrier providing the profile recognitions (elements)
        into which the trace is projected.

    Semantics
    ---------
    Acts: TraceProfile = (CompleteTrace ProfileRecognitions).

    We realize this by:
    - requiring that trace is well-formed (CompleteTrace) and that
      trace.elements ⊆ profile_topos.elements (ProfileRecognitions),
    - packaging the pair into a trace_profile carrier that records:

        trace_id = trace.id
        profile_topos_id = profile_topos.id
        elements = trace.elements
    """
    trace = inputs.get("trace")
    profile_topos = inputs.get("profile_topos")
    if trace is None or profile_topos is None:
        raise KeyError("trace_profile requires 'trace' and 'profile_topos' inputs")
    if trace.get("kind") != "trace":
        raise LawValidationError("trace_profile trace input must have kind 'trace'")
    if profile_topos.get("kind") != "profile_topos":
        raise LawValidationError("trace_profile profile_topos input must have kind 'profile_topos'")

    validate_trace(trace)
    elements: List[str] = list(trace.get("elements", []))
    profile_elements = set(profile_topos.get("elements", []))
    missing = [e for e in elements if e not in profile_elements]
    if missing:
        raise LawValidationError(
            f"trace_profile requires all trace elements to be profile recognitions; missing {missing}"
        )

    payload = {
        "kind": "trace_profile",
        "trace_id": trace["id"],
        "profile_topos_id": profile_topos["id"],
        "elements": elements,
        "act_ref": "TraceProfile",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "trace_profile",
            "src": trace["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "trace_profile",
            "src": profile_topos["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"trace_profile": payload["id"]},
    )

