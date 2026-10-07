from __future__ import annotations

from typing import Dict, Set

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _collect_variables(node: object) -> Set[str]:
    """
    Collect variable names from a minimal term AST.

    We restrict to the tiny fragment needed for the initial syntax layer:

    - variable nodes: {"tag": "var", "name": <str>}
    - application nodes: {"tag": "app", "subterms": [fn, arg]}
    - function nodes: {"tag": "fun", "param": <str>, "body": <node>}

    Any other shape is treated as a hard error rather than being
    heuristically interpreted.
    """
    if isinstance(node, dict):
        tag = node.get("tag")
        if not isinstance(tag, str):
            raise LawValidationError("syntax node must provide string 'tag'")
        if tag == "var":
            name = node.get("name")
            if not isinstance(name, str):
                raise LawValidationError("var node must provide string 'name'")
            return {name}
        if tag == "app":
            subterms = node.get("subterms")
            if not isinstance(subterms, list):
                raise LawValidationError("app node must use list 'subterms'")
            if len(subterms) != 2:
                raise LawValidationError("app node must have exactly two subterms [fn, arg]")
            acc: Set[str] = set()
            for child in subterms:
                acc |= _collect_variables(child)
            return acc
        if tag == "fun":
            param = node.get("param")
            if not isinstance(param, str):
                raise LawValidationError("fun node must provide string 'param'")
            body = node.get("body")
            if body is None:
                raise LawValidationError("fun node must provide 'body'")
            # Parameter occurrences are discovered via var nodes in the body.
            return _collect_variables(body)
        raise LawValidationError(f"unknown syntax tag {tag!r} in minimal term fragment")
    if isinstance(node, list):
        acc: Set[str] = set()
        for child in node:
            acc |= _collect_variables(child)
        return acc
    # Scalars (ints/strings/etc.) are not treated as term nodes.
    return set()


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    RecognizeSyntax realizer.

    Inputs
    ------
    term:
        Term carrier (kind ``term``) whose syntax and bindings are to be
        checked against the minimal binding discipline.

    Semantics
    ---------
    - Enforce that the payload has kind ``term``.
    - Interpret ``syntax`` as a minimal AST built from variable and
      composite nodes (see ``_collect_variables``).
    - Extract the set of variable names appearing in the AST.
    - Require that the ``bindings`` array lists each variable exactly once,
      via objects of the form {"name": <str>}.
    - Emit a ``syntax_recognition_evidence`` node recording the variable
      set and binding discipline, with status \"pass\" when the checks
      succeed and \"fail\" otherwise.

    This is a closed-world fragment: terms using other constructors are
    rejected rather than interpreted heuristically.
    """
    term = inputs.get("term")
    if term is None:
        raise KeyError("recognize_syntax requires 'term' input")
    if term.get("kind") != "term":
        raise LawValidationError("recognize_syntax input must have kind 'term'")

    syntax = term.get("syntax")
    bindings = term.get("bindings")
    if not isinstance(bindings, list):
        raise LawValidationError("term.bindings must be a list")

    vars_in_syntax = _collect_variables(syntax)

    bound_names: Set[str] = set()
    duplicate_names: Set[str] = set()
    for entry in bindings:
        if not isinstance(entry, dict):
            raise LawValidationError("each binding entry must be an object")
        name = entry.get("name")
        if not isinstance(name, str):
            raise LawValidationError("each binding entry must provide string 'name'")
        if name in bound_names:
            duplicate_names.add(name)
        bound_names.add(name)

    missing = sorted(vars_in_syntax - bound_names)
    extra = sorted(bound_names - vars_in_syntax)
    duplicates = sorted(duplicate_names)

    status = "pass"
    if missing or extra or duplicates:
        status = "fail"

    witnesses: Dict[str, object] = {
        "variables_in_syntax": sorted(vars_in_syntax),
        "bound_variables": sorted(bound_names),
        "missing_bindings": missing,
        "extra_bindings": extra,
        "duplicate_bindings": duplicates,
    }

    evidence = {
        "kind": "syntax_recognition_evidence",
        "syntax_id": term["id"],
        "witnesses": witnesses,
        "status": status,
        "act_ref": "RecognizeSyntax",
    }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "recognize_syntax",
        "src": term["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"syntax_recognition_evidence": evidence["id"]},
    )
