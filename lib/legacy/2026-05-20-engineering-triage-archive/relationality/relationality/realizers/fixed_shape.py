from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    fixed_shape realizer.

    Inputs
    ------
    flow_map:
        FlowMap carrier encoding flow on a recognition lattice.
    nucleus_map:
        NucleusMap carrier encoding the nucleus on the same lattice.
    shuffle_profile:
        ShuffleProfile carrier describing shuffle-stable recognitions.

    Semantics
    ---------
    Acts: FixedShape = (EnsureFixedPoint ShuffleIndexImplication).

    In the full theory, FixedShape is obtained by applying a fixed-point
    construction to the shuffle-indexed implication operator. Here we realize
    a minimal, act-consistent approximation:

        invariant_elements = { e in ⋃classes | flow_map.flow_table[e] == e }

    i.e. elements which:
    - lie in the shuffle profile (some class), and
    - are fixed by the flow.

    We require at least one such element. Nucleus compatibility is recorded
    via the nucleus_ref; detailed fixed-point iteration remains the
    responsibility of the shuffle/trace/flow law-checkers.
    """
    flow_map = inputs.get("flow_map")
    nucleus_map = inputs.get("nucleus_map")
    shuffle_profile = inputs.get("shuffle_profile")
    if flow_map is None or nucleus_map is None or shuffle_profile is None:
        raise KeyError("fixed_shape requires 'flow_map', 'nucleus_map', and 'shuffle_profile' inputs")
    if flow_map.get("kind") != "flow_map":
        raise LawValidationError("fixed_shape flow_map input must have kind 'flow_map'")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("fixed_shape nucleus_map input must have kind 'nucleus_map'")
    if shuffle_profile.get("kind") != "shuffle_profile":
        raise LawValidationError("fixed_shape shuffle_profile input must have kind 'shuffle_profile'")

    shuffle_classes = shuffle_profile.get("classes") or []
    if not shuffle_classes:
        raise LawValidationError("fixed_shape requires non-empty classes on shuffle_profile")
    shuffle_elements = {e for cls in shuffle_classes for e in cls}

    flow_table = flow_map.get("flow_table") or {}
    invariant_elements: List[str] = []
    for e in sorted(shuffle_elements):
        image = flow_table.get(e)
        if image is None:
            raise LawValidationError("fixed_shape requires flow_table to be total on shuffle_profile elements")
        if image == e:
            invariant_elements.append(e)

    if not invariant_elements:
        raise LawValidationError("fixed_shape found no elements stable under flow within the shuffle profile")

    payload = {
        "kind": "fixed_shape",
        "invariant_elements": invariant_elements,
        "flow_ref": flow_map["id"],
        "nucleus_ref": nucleus_map["id"],
        "shuffle_ref": shuffle_profile["id"],
        "act_ref": "FixedShape",
    }
    ensure_id_coherence(payload)

    edge = {
        "operator": "fixed_shape",
        "src": shuffle_profile["id"],
        "tgt": payload["id"],
    }

    return RealizerOutput(
        nodes=[payload],
        edges=[edge],
        bindings={"fixed_shape": payload["id"]},
    )

