from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    evaluate_judgment realizer.

    Inputs
    ------
    judgment:
        Judgment carrier (kind ``judgment``) to be evaluated.

    Semantics
    ---------
    Realizes the EvaluateJudgment act by tying the typing judgment to the
    normalization pipeline:

    - The input judgment carries ``term_id`` and ``type_id``.
    - The term referenced by ``term_id`` must have been recognized and
      normalized via RecognizeSyntax/NormalizeSyntax, yielding a
      ``syntax_normal_form`` node in the graph.
    - This normal form serves as the evaluation witness for the judgment:
      evaluating a judgment means evaluating (normalizing) its term while
      preserving the type.

    The realizer therefore:
    - looks up the term and its syntax_normal_form in the graph; and
    - emits an evaluated_judgment whose evaluation_witness_id is the
      syntax_normal_form.id.
    """
    judgment = inputs.get("judgment")
    if judgment is None:
        raise KeyError("evaluate_judgment requires 'judgment' input")
    if judgment.get("kind") != "judgment":
        raise LawValidationError("evaluate_judgment input must have kind 'judgment'")

    term_id = judgment.get("term_id")
    if not isinstance(term_id, str):
        raise LawValidationError("judgment.term_id must be a string")
    term = getattr(graph, "nodes", {}).get(term_id)
    if term is None or term.get("kind") != "term":
        raise LawValidationError("evaluate_judgment requires the judgment.term_id to reference a term node in the graph")

    # Require that the term has already been normalized via NormalizeSyntax
    # so that evaluation_witness_id can point at a syntax_normal_form node.
    syntax_nf_id = None
    for node in getattr(graph, "nodes", {}).values():
        if node.get("kind") == "syntax_normal_form" and node.get("term_id") == term_id:
            if syntax_nf_id is not None:
                raise LawValidationError(
                    "evaluate_judgment found multiple syntax_normal_form nodes for the same term"
                )
            syntax_nf_id = node["id"]
    if syntax_nf_id is None:
        raise LawValidationError(
            "evaluate_judgment requires a syntax_normal_form node for the judgment.term_id"
        )

    evaluated = {
        "kind": "evaluated_judgment",
        "judgment_id": judgment["id"],
        "evaluation_witness_id": syntax_nf_id,
        "act_ref": "EvaluateJudgment",
    }
    ensure_id_coherence(evaluated)

    edge = {
        "operator": "evaluate_judgment",
        "src": judgment["id"],
        "tgt": evaluated["id"],
    }

    return RealizerOutput(
        nodes=[evaluated],
        edges=[edge],
        bindings={"evaluated_judgment": evaluated["id"]},
    )
