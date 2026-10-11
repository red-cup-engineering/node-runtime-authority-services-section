from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_trace


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    build_evaluation_context realizer.

    Inputs
    ------
    trace:
        Trace carrier providing head/tail decomposition.
    eval_context_seed:
        Seed frame carrier (kind ``eval_context_seed``) specifying an initial
        hole_position and typing witness.

    Semantics
    ---------
    Construct an evaluation_context whose frames enumerate every position in
    trace.elements, with:
    - hole_position = index in elements;
    - frame_context = {'focus': elements[i]};
    - typing_ref = seed.typing_ref.
    """
    trace = inputs.get("trace")
    seed = inputs.get("eval_context_seed")
    if trace is None or seed is None:
        raise KeyError("build_evaluation_context requires 'trace' and 'eval_context_seed' inputs")
    if trace.get("kind") != "trace":
        raise LawValidationError("build_evaluation_context trace input must have kind 'trace'")
    if seed.get("kind") != "eval_context_seed":
        raise LawValidationError("build_evaluation_context eval_context_seed input must have kind 'eval_context_seed'")

    validate_trace(trace)
    elements: List[str] = list(trace.get("elements", []))
    if not elements:
        raise LawValidationError("build_evaluation_context requires non-empty trace.elements")

    typing_ref = seed.get("typing_ref")
    frames: List[dict] = []
    for idx, element in enumerate(elements):
        frame = {
            "kind": "evaluation_frame",
            "trace_id": trace["id"],
            "hole_position": idx,
            "frame_context": {"focus": element},
            "typing_ref": typing_ref,
        }
        ensure_id_coherence(frame)
        frames.append(frame)

    eval_ctx = {
        "kind": "evaluation_context",
        "trace_id": trace["id"],
        "frames": frames,
        "frame_ordering": list(range(len(frames))),
    }
    ensure_id_coherence(eval_ctx)

    edge = {
        "operator": "build_evaluation_context",
        "src": trace["id"],
        "tgt": eval_ctx["id"],
    }

    nodes: List[dict] = [eval_ctx] + frames

    return RealizerOutput(
        nodes=nodes,
        edges=[edge],
        bindings={"evaluation_context": eval_ctx["id"]},
    )

