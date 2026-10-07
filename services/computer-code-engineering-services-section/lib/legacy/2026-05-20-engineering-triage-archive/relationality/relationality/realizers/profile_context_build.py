from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_context_build realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the underlying lattice.
    profile_semantics:
        ProfileSemantics carrier packaging classifier/limits and witnesses
        for the same profile_topos.

    Semantics
    ---------
    Constructs a profile_context carrier tying the profile semantics to the
    normalization/equivalence layer. The context is purely referential:

        profile_topos_id = profile_topos.id
        profile_semantics_id = profile_semantics.id

    and cites the contextualized normalization act as its act_ref.
    """
    profile = inputs.get("profile_topos")
    semantics = inputs.get("profile_semantics")
    if profile is None or semantics is None:
        raise KeyError("profile_context_build requires 'profile_topos' and 'profile_semantics' inputs")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("profile_context_build profile_topos input must have kind 'profile_topos'")
    if semantics.get("kind") != "profile_semantics":
        raise LawValidationError("profile_context_build profile_semantics input must have kind 'profile_semantics'")

    profile_id = profile["id"]
    if semantics.get("profile_topos_id") != profile_id:
        raise LawValidationError(
            "profile_context_build requires profile_semantics.profile_topos_id to match profile_topos.id"
        )

    payload = {
        "kind": "profile_context",
        "profile_topos_id": profile_id,
        "profile_semantics_id": semantics["id"],
        "act_ref": "ContextualizeNormalizeObservationEquivalence",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "profile_context_build",
            "src": profile_id,
            "tgt": payload["id"],
        },
        {
            "operator": "profile_context_build",
            "src": semantics["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"profile_context": payload["id"]},
    )

