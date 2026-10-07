from __future__ import annotations

from typing import Dict, Set

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError
from relationality.realizers.recognize_syntax import _collect_variables
from relationality.realizers.reduce import _substitute


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    substitution_term realizer.

    Inputs
    ------
    term:
        Term carrier (kind ``term``) whose syntax is to be rewritten.
    substitution_map:
        SubstitutionMap carrier (kind ``substitution_map``) mapping variable
        names to replacement term IDs.

    Semantics
    ---------
    - Enforce that every variable appearing in term.syntax has a binding in
      substitution_map.bindings.
    - For each binding var → term_id, use the minimal substitution fragment
      from Reduce (_substitute) to compute a capture-avoiding substitution on
      the AST, respecting binders (fun parameters).
    - Rebuild bindings from the resulting AST.
    - Emit substitution_evidence recording the applied bindings.
    """
    term = inputs.get("term")
    substitution_map = inputs.get("substitution_map")
    if term is None or substitution_map is None:
        raise KeyError("substitution_term requires 'term' and 'substitution_map' inputs")
    if term.get("kind") != "term":
        raise LawValidationError("substitution_term input 'term' must have kind 'term'")
    if substitution_map.get("kind") != "substitution_map":
        raise LawValidationError("substitution_term input 'substitution_map' must have kind 'substitution_map'")

    context_id = term.get("context_id")
    if substitution_map.get("context_id") != context_id:
        raise LawValidationError("substitution_map.context_id must match term.context_id")

    bindings = substitution_map.get("bindings") or {}
    if not isinstance(bindings, dict):
        raise LawValidationError("substitution_map.bindings must be a mapping")

    # Totality on variables appearing in the term syntax.
    vars_in_syntax: Set[str] = _collect_variables(term.get("syntax"))
    missing = vars_in_syntax - set(bindings.keys())
    if missing:
        raise LawValidationError(
            f"substitution_map missing bindings for variables {sorted(missing)} in term.syntax"
        )

    # Apply substitutions in deterministic order over variable names.
    new_syntax = term.get("syntax")
    for var in sorted(bindings.keys()):
        replacement_id = bindings[var]
        replacement = graph.nodes.get(replacement_id)
        if replacement is None:
            raise KeyError(f"replacement term {replacement_id!r} not found in graph")
        if replacement.get("kind") != "term":
            raise LawValidationError("substitution_map bindings must map to term carriers")
        if replacement.get("context_id") != context_id:
            raise LawValidationError(
                "replacement term context_id must match original term.context_id"
            )
        new_syntax = _substitute(new_syntax, var, replacement.get("syntax"))

    # Rebuild bindings from the rewritten syntax.
    new_vars: Set[str] = _collect_variables(new_syntax)
    new_bindings_list = [{"name": name} for name in sorted(new_vars)]

    new_term = {
        "kind": "term",
        "syntax": new_syntax,
        "context_id": context_id,
        "trace_id": term.get("trace_id"),
        "bindings": new_bindings_list,
    }
    ensure_id_coherence(new_term)

    evidence = {
        "kind": "substitution_evidence",
        "term_id": term["id"],
        "substitution_map_id": substitution_map["id"],
        "bindings": dict(bindings),
        "typing_witnesses": {},
        "status": "pass",
        "act_ref": "SubstitutionTerm",
    }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "substitution_term",
        "src": term["id"],
        "tgt": new_term["id"],
        "evidence_ids": [evidence["id"]],
    }

    return RealizerOutput(
        nodes=[new_term, evidence],
        edges=[edge],
        bindings={
            "term": new_term["id"],
            "substitution_evidence": evidence["id"],
        },
    )

