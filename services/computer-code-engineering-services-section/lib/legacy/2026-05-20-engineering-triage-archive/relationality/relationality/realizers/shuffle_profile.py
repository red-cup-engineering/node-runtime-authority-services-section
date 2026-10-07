from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _identity_partition(elements: List[str]) -> tuple[List[List[str]], List[str]]:
    """
    Construct the trivial shuffle equivalence where each element forms its own
    singleton class. This is the lexicographically minimal partition and is a
    lawful ShuffleProfileRecognitions carrier in the absence of explicit
    shuffle equivalence data.
    """
    classes = [[e] for e in elements]
    reps = list(elements)
    return classes, reps


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    shuffle_profile realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the recognition lattice.

    Semantics
    ---------
    Acts: ShuffleProfileRecognitions = (FixFlowNucleus CollapseShuffle).

    At the carrier level, a shuffle_profile object encodes equivalence classes
    of recognitions whose stabilized traces are identified by admissible
    shuffles. In this code model we do not yet materialize non-trivial shuffle
    equivalence (that is handled by shuffle_equivalence_evidence and the trace
    realizers); instead, we construct the identity partition:

        classes = [[e] for e in profile_topos.elements]
        canonical_reps = profile_topos.elements

    This is the unique minimal shuffle_profile consistent with the acts when
    no additional shuffle equivalence has been recorded on the profile.
    """
    profile = inputs.get("profile_topos")
    if profile is None:
        raise KeyError("shuffle_profile requires 'profile_topos' input")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("shuffle_profile profile_topos input must have kind 'profile_topos'")

    elements = list(profile.get("elements", []))
    if not elements:
        raise LawValidationError("shuffle_profile requires non-empty profile_topos.elements")

    classes, reps = _identity_partition(elements)

    payload = {
        "kind": "shuffle_profile",
        "profile_id": profile["id"],
        "classes": classes,
        "canonical_reps": reps,
        "act_ref": "ShuffleProfileRecognitions",
    }
    ensure_id_coherence(payload)

    edge = {
        "operator": "shuffle_profile",
        "src": profile["id"],
        "tgt": payload["id"],
    }

    return RealizerOutput(
        nodes=[payload],
        edges=[edge],
        bindings={"shuffle_profile": payload["id"]},
    )

