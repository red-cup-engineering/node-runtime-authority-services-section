from __future__ import annotations

from typing import Dict

from relationality.realizer_output import RealizerOutput

from ._temporal_modality_common import build_temporal_modality


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    flow_map = inputs.get("flow_map")
    nucleus_map = inputs.get("nucleus_map")
    fixed_invariants = inputs.get("fixed_invariants")
    if flow_map is None or nucleus_map is None or fixed_invariants is None:
        raise KeyError("eventually_modality requires flow_map, nucleus_map, and fixed_invariants inputs")
    return build_temporal_modality(
        graph,
        flow_map=flow_map,
        nucleus_map=nucleus_map,
        fixed_invariants=fixed_invariants,
        operator="eventually_modality",
    )

