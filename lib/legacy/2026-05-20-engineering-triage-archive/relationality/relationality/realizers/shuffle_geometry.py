from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    shuffle_geometry realizer.

    Inputs
    ------
    shuffle_profile:
        ShuffleProfile carrier describing shuffle equivalence classes.

    Semantics
    ---------
    Acts: ShuffleGeometry = (StructureSemantics CommuteShuffleFlowAndNucleus).

    In the full theory, geometry tags would record how ShuffleFlow and Nucleate
    act on each shuffle class. In this code model we attach a minimal, purely
    structural tag to each canonical representative:

        geometry_tags[rep] = "shuffle_class"

    This witnesses that each class carries a well-formed geometric label and
    that geometry is indexed by shuffle classes, as required by the README.
    """
    shuffle_profile = inputs.get("shuffle_profile")
    if shuffle_profile is None:
        raise KeyError("shuffle_geometry requires 'shuffle_profile' input")
    if shuffle_profile.get("kind") != "shuffle_profile":
        raise LawValidationError("shuffle_geometry shuffle_profile input must have kind 'shuffle_profile'")

    reps = shuffle_profile.get("canonical_reps") or []
    if not reps:
        raise LawValidationError("shuffle_geometry requires non-empty canonical_reps on shuffle_profile")

    geometry_tags = {rep: "shuffle_class" for rep in reps}

    payload = {
        "kind": "shuffle_geometry",
        "shuffle_profile_id": shuffle_profile["id"],
        "geometry_tags": geometry_tags,
        "act_ref": "ShuffleGeometry",
    }
    ensure_id_coherence(payload)

    edge = {
        "operator": "shuffle_geometry",
        "src": shuffle_profile["id"],
        "tgt": payload["id"],
    }

    return RealizerOutput(
        nodes=[payload],
        edges=[edge],
        bindings={"shuffle_geometry": payload["id"]},
    )

