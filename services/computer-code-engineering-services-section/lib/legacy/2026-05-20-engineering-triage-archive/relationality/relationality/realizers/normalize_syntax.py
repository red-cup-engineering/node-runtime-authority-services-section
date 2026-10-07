from __future__ import annotations

from typing import Dict, Tuple

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError
from relationality.realizers.reduce import _substitute


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    NormalizeSyntax realizer.

    Inputs
    ------
    term:
        Term carrier (kind ``term``) to be normalized.

    Semantics
    ---------
    Normalization is defined as β-normalization on the minimal AST
    fragment accepted by ``recognize_syntax`` using a deterministic
    leftmost-outermost strategy:

    - The term fragment consists of:
      - var: {\"tag\": \"var\", \"name\": <str>}
      - app: {\"tag\": \"app\", \"subterms\": [fn, arg]}
      - fun: {\"tag\": \"fun\", \"param\": <str>, \"body\": <node>}
    - A single β-step reduces ``((fun param. body) arg)`` to
      ``body[arg/param]`` using the same substitution kernel as the
      Reduce act.
    - Normalization repeatedly applies that step in a leftmost-outermost
      manner until no β-redex remains.

    On well-typed terms in this fragment, the Acts (NormalizeStrongly,
    Reduce, EvaluateJudgment) guarantee strong normalization, so this
    strategy is terminating; idempotence follows because the resulting
    term contains no further redexes.

    To ensure the normalization witness is explicit, this realizer still
    expects a pre-existing ``syntax_recognition_evidence`` node linked to
    the term. The caller is responsible for seeding that node in the
    graph (typically via the ``recognize_syntax`` runbook).
    """
    term = inputs.get("term")
    if term is None:
        raise KeyError("normalize_syntax requires 'term' input")
    if term.get("kind") != "term":
        raise LawValidationError("normalize_syntax input must have kind 'term'")

    # Look for a syntax_recognition_evidence node associated with this term.
    term_id = term["id"]
    normalization_witness_id = None
    for edge in getattr(graph, "edges", {}).values():
        if getattr(edge, "operator", None) == "recognize_syntax" and edge.src == term_id:
            normalization_witness_id = edge.tgt
            break

    if normalization_witness_id is None:
        raise LawValidationError(
            "normalize_syntax requires existing syntax_recognition_evidence edge from term"
        )

    def _beta_reduce_once(node: object) -> Tuple[object, bool]:
        """
        Perform a single leftmost-outermost beta-reduction step on the
        minimal term fragment, returning (new_node, changed).
        """
        if isinstance(node, dict):
            tag = node.get("tag")
            if tag == "app":
                subterms = node.get("subterms")
                if not isinstance(subterms, list) or len(subterms) != 2:
                    raise LawValidationError("app node must have exactly two subterms [fn, arg]")
                fn, arg = subterms
                if isinstance(fn, dict) and fn.get("tag") == "fun":
                    param = fn.get("param")
                    body = fn.get("body")
                    if not isinstance(param, str):
                        raise LawValidationError("fun node must provide string 'param'")
                    if body is None:
                        raise LawValidationError("fun node must provide 'body'")
                    return _substitute(body, param, arg), True
                # Otherwise, reduce inside fn, then arg.
                new_fn, changed = _beta_reduce_once(fn)
                if changed:
                    return {"tag": "app", "subterms": [new_fn, arg]}, True
                new_arg, changed = _beta_reduce_once(arg)
                if changed:
                    return {"tag": "app", "subterms": [fn, new_arg]}, True
                return dict(node), False
            if tag == "fun":
                param = node.get("param")
                if not isinstance(param, str):
                    raise LawValidationError("fun node must provide string 'param'")
                body = node.get("body")
                if body is None:
                    raise LawValidationError("fun node must provide 'body'")
                new_body, changed = _beta_reduce_once(body)
                if changed:
                    return {"tag": "fun", "param": param, "body": new_body}, True
                return dict(node), False
            if tag == "var":
                return dict(node), False
            raise LawValidationError(f"unknown syntax tag {tag!r} in NormalizeSyntax fragment")
        if isinstance(node, list):
            new_list = []
            changed_any = False
            for child in node:
                new_child, changed = _beta_reduce_once(child)
                if changed:
                    changed_any = True
                new_list.append(new_child)
            return new_list, changed_any
        return node, False

    # Compute β-normal form by iterating the single-step reducer until
    # it reports no change. On strongly normalizing terms this terminates
    # and produces a unique normal form for the chosen strategy.
    normal_form = term.get("syntax")
    while True:
        normal_form, changed = _beta_reduce_once(normal_form)
        if not changed:
            break
    syntax_nf = {
        "kind": "syntax_normal_form",
        "term_id": term_id,
        "normal_form": normal_form,
        "normalization_witness_id": normalization_witness_id,
        "act_ref": "NormalizeSyntax",
    }
    ensure_id_coherence(syntax_nf)

    edge = {
        "operator": "normalize_syntax",
        "src": term_id,
        "tgt": syntax_nf["id"],
    }

    return RealizerOutput(
        nodes=[syntax_nf],
        edges=[edge],
        bindings={"syntax_normal_form": syntax_nf["id"]},
    )
