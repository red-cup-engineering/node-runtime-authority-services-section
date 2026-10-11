from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    StartTrace realizer.

    Inputs
    ------
    seed:
        Any carrier whose ``id`` is used as the first trace element.

    Semantics
    ---------
    Constructs a minimal trace ``t = [h]`` satisfying the head/tail axioms:
    - elements = [seed_id]
    - head = seed_id
    - tail = []
    - shuffle_metadata initialized to the identity permutation.
    """
    seed = inputs.get("seed")
    if seed is None:
        raise KeyError("start_trace requires `seed` input")
    seed_id = seed.get("id")
    if not isinstance(seed_id, str):
        raise LawValidationError("start_trace seed must carry a string `id`")

    elements = [seed_id]
    trace = {
        "kind": "trace",
        "elements": elements,
        "head": seed_id,
        "tail": [],
        "shuffle_metadata": {
            "permutations": [list(range(len(elements)))],
            "canonical_rep": seed_id,
        },
    }
    ensure_id_coherence(trace)

    edge = {
        "operator": "start_trace",
        "src": seed_id,
        "tgt": trace["id"],
    }

    return RealizerOutput(
        nodes=[trace],
        edges=[edge],
        bindings={"trace": trace["id"]},
    )
