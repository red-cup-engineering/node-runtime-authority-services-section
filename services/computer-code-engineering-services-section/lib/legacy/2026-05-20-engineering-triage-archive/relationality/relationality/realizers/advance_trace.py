from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _validate_input_trace(trace: dict) -> None:
    if trace.get("kind") != "trace":
        raise LawValidationError("advance_trace requires `trace` input of kind 'trace'")
    elements: List[str] = trace.get("elements", [])
    head = trace.get("head")
    tail = trace.get("tail", [])
    if not isinstance(elements, list) or not elements:
        raise LawValidationError("advance_trace input trace must contain at least one element")
    if elements[0] != head:
        raise LawValidationError("advance_trace input trace violates head = elements[0]")
    if elements[1:] != tail:
        raise LawValidationError("advance_trace input trace violates tail = elements[1:]")


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    AdvanceTrace realizer.

    Inputs
    ------
    trace:
        Existing trace carrier.
    seed:
        New head element; its ``id`` becomes the new head of the trace.

    Semantics
    ---------
    Given a trace ``t`` with head ``h`` and tail ``T``, and a new head ``h'``,
    produce a new trace with:
    - elements = [h'] + elements(t)
    - head = h'
    - tail = elements(t)
    preserving shuffle metadata by lifting permutations to the extended sequence.
    """
    trace = inputs.get("trace")
    seed = inputs.get("seed")
    if trace is None or seed is None:
        raise KeyError("advance_trace requires `trace` and `seed` inputs")
    _validate_input_trace(trace)

    seed_id = seed.get("id")
    if not isinstance(seed_id, str):
        raise LawValidationError("advance_trace seed must carry a string `id`")

    old_elements: List[str] = list(trace["elements"])
    new_elements: List[str] = [seed_id] + old_elements
    new_trace: dict = {
        "kind": "trace",
        "elements": new_elements,
        "head": seed_id,
        "tail": new_elements[1:],
    }

    shuffle = trace.get("shuffle_metadata")
    if shuffle is not None:
        perms = shuffle.get("permutations", [])
        lifted_perms: List[List[int]] = []
        length_old = len(old_elements)
        for perm in perms:
            if sorted(perm) != list(range(length_old)):
                raise LawValidationError("advance_trace input trace has invalid shuffle permutation")
            lifted_perms.append([0] + [idx + 1 for idx in perm])
        new_shuffle: dict = {"permutations": lifted_perms}
        canonical_rep = shuffle.get("canonical_rep")
        if canonical_rep is not None:
            if canonical_rep not in old_elements:
                raise LawValidationError("advance_trace input trace has invalid canonical_rep")
            new_shuffle["canonical_rep"] = canonical_rep
        new_trace["shuffle_metadata"] = new_shuffle
    else:
        new_trace["shuffle_metadata"] = {
            "permutations": [list(range(len(new_elements)))],
            "canonical_rep": trace["head"],
        }

    ensure_id_coherence(new_trace)

    edges = [
        {
            "operator": "advance_trace",
            "src": trace["id"],
            "tgt": new_trace["id"],
        },
        {
            "operator": "advance_trace",
            "src": seed_id,
            "tgt": new_trace["id"],
        },
    ]

    return RealizerOutput(
        nodes=[new_trace],
        edges=edges,
        bindings={"trace": new_trace["id"]},
    )

