from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_entropy realizer.

    Inputs
    ------
    trace:
        Trace carrier describing the profile trace.
    profile_entropy:
        ProfileEntropy carrier produced by profile_entropy_measure, giving an
        entropy value for each profile recognition.

    Semantics
    ---------
    Acts: ProfileEntropy = (TraceProfile ProfileEntropyMeasure).

    We propagate the entropy measure along the trace by:
    - requiring that every trace element is one of the keys of
      profile_entropy.entropy_values;
    - constructing a new profile_entropy carrier whose entropy_values are
      restricted to the subset of elements actually appearing along the trace.

    This yields an entropy functional over the trace of recognitions inside
    the profile.
    """
    trace = inputs.get("trace")
    profile_entropy = inputs.get("profile_entropy")
    if trace is None or profile_entropy is None:
        raise KeyError("profile_entropy requires 'trace' and 'profile_entropy' inputs")
    if trace.get("kind") != "trace":
        raise LawValidationError("profile_entropy trace input must have kind 'trace'")
    if profile_entropy.get("kind") != "profile_entropy":
        raise LawValidationError("profile_entropy profile_entropy input must have kind 'profile_entropy'")

    entropy_values = profile_entropy.get("entropy_values") or {}
    if not entropy_values:
        raise LawValidationError("profile_entropy requires non-empty entropy_values in profile_entropy carrier")

    elements = trace.get("elements") or []
    if not elements:
        raise LawValidationError("profile_entropy requires non-empty trace.elements")

    missing = [e for e in elements if e not in entropy_values]
    if missing:
        raise LawValidationError(
            f"profile_entropy found trace elements without entropy assignments: {missing}"
        )

    restricted_values = {e: entropy_values[e] for e in elements}

    payload = {
        "kind": "profile_entropy",
        "profile_id": profile_entropy["profile_id"],
        "entropy_values": restricted_values,
        "act_ref": "ProfileEntropy",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "profile_entropy",
            "src": trace["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "profile_entropy",
            "src": profile_entropy["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"profile_entropy": payload["id"]},
    )

