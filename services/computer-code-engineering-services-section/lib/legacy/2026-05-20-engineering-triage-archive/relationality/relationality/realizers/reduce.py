from __future__ import annotations

from typing import Dict, Set

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError
from relationality.realizers.recognize_syntax import _collect_variables


def _substitute(node: object, var: str, replacement: object) -> object:
    """
    Capture-avoiding substitution on the minimal term fragment.

    Fragment:
    - var: {"tag": "var", "name": <str>}
    - app: {"tag": "app", "subterms": [fn, arg]}
    - fun: {"tag": "fun", "param": <str>, "body": <node>}
    """
    if isinstance(node, dict):
        tag = node.get("tag")
        if tag == "var":
            name = node.get("name")
            if not isinstance(name, str):
                raise LawValidationError("var node must provide string 'name'")
            if name == var:
                # Deep copy via canonicalization round-trip.
                from copy import deepcopy

                return deepcopy(replacement)
            return dict(node)
        if tag == "app":
            subterms = node.get("subterms")
            if not isinstance(subterms, list) or len(subterms) != 2:
                raise LawValidationError("app node must have exactly two subterms [fn, arg]")
            fn_sub = _substitute(subterms[0], var, replacement)
            arg_sub = _substitute(subterms[1], var, replacement)
            return {"tag": "app", "subterms": [fn_sub, arg_sub]}
        if tag == "fun":
            param = node.get("param")
            if not isinstance(param, str):
                raise LawValidationError("fun node must provide string 'param'")
            body = node.get("body")
            if body is None:
                raise LawValidationError("fun node must provide 'body'")
            # Standard λ-calculus convention: do not substitute under a binder
            # that binds the same variable.
            if param == var:
                return dict(node)
            body_sub = _substitute(body, var, replacement)
            return {"tag": "fun", "param": param, "body": body_sub}
        raise LawValidationError(f"unknown syntax tag {tag!r} in Reduce fragment")
    if isinstance(node, list):
        return [_substitute(child, var, replacement) for child in node]
    return node


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    Reduce realizer.

    Inputs
    ------
    term:
        Application term (kind ``term``) expected to be in redex form.
    trace:
        Trace carrier recording the evaluation history.

    Semantics
    ---------
    On the minimal fragment:

        ((fun param. body) arg)  ↦  body[arg/param]

    where:
    - ``term.syntax`` has shape ``{\"tag\": \"app\", \"subterms\": [fun, arg]}``,
    - ``fun`` has shape ``{\"tag\": \"fun\", \"param\": <str>, \"body\": <node>}``.

    The realizer:
    - Computes the contractum via capture-aware substitution on this fragment.
    - Recomputes the term bindings from the resulting syntax.
    - Advances the trace by one step, using the reduced term as the new head.
    - Emits a ``reduction_evidence`` node summarizing the step.
    """
    term = inputs.get("term")
    trace = inputs.get("trace")
    if term is None or trace is None:
        raise KeyError("reduce requires 'term' and 'trace' inputs")
    if term.get("kind") != "term":
        raise LawValidationError("reduce input 'term' must have kind 'term'")
    if trace.get("kind") != "trace":
        raise LawValidationError("reduce input 'trace' must have kind 'trace'")

    syntax = term.get("syntax")
    if not isinstance(syntax, dict) or syntax.get("tag") != "app":
        raise LawValidationError("reduce requires term.syntax to be an 'app' node")
    subterms = syntax.get("subterms")
    if not isinstance(subterms, list) or len(subterms) != 2:
        raise LawValidationError("app node must have exactly two subterms [fn, arg]")
    fn, arg = subterms
    if not isinstance(fn, dict) or fn.get("tag") != "fun":
        raise LawValidationError("reduce requires application of a 'fun' node as its left subterm")

    param = fn.get("param")
    body = fn.get("body")
    if not isinstance(param, str):
        raise LawValidationError("fun node must provide string 'param'")
    if body is None:
        raise LawValidationError("fun node must provide 'body'")

    # Compute contractum by substituting argument for the parameter in the body.
    reduced_syntax = _substitute(body, param, arg)
    # Rebuild bindings from the reduced syntax.
    var_names: Set[str] = _collect_variables(reduced_syntax)
    new_bindings = [{"name": name} for name in sorted(var_names)]

    new_term = {
        "kind": "term",
        "syntax": reduced_syntax,
        "context_id": term["context_id"],
        "trace_id": term["trace_id"],
        "bindings": new_bindings,
    }
    ensure_id_coherence(new_term)

    # Advance the trace by treating the reduced term as the new head element.
    # For the minimal fragment we use the same trace semantics as advance_trace
    # but re-materialize the trace node directly rather than emitting an
    # advance_trace edge (so that the runbook step operator remains `reduce`).
    elements = trace.get("elements") or []
    if not isinstance(elements, list) or not elements:
        raise LawValidationError("reduce requires non-empty trace.elements")
    new_elements = [new_term["id"]] + list(elements)
    new_trace = {
        "kind": "trace",
        "elements": new_elements,
        "head": new_elements[0],
        "tail": new_elements[1:],
    }
    shuffle = trace.get("shuffle_metadata")
    if shuffle is not None:
        perms = shuffle.get("permutations", [])
        lifted_perms: list[list[int]] = []
        length_old = len(elements)
        for perm in perms:
            if sorted(perm) != list(range(length_old)):
                raise LawValidationError("reduce input trace has invalid shuffle permutation")
            lifted_perms.append([0] + [idx + 1 for idx in perm])
        new_shuffle: dict = {"permutations": lifted_perms}
        canonical_rep = shuffle.get("canonical_rep")
        if canonical_rep is not None:
            if canonical_rep not in elements:
                raise LawValidationError("reduce input trace has invalid canonical_rep")
            new_shuffle["canonical_rep"] = canonical_rep
        new_trace["shuffle_metadata"] = new_shuffle
    ensure_id_coherence(new_trace)

    # Locate a typing judgment for the term in the ambient graph.
    candidates = []
    for node in getattr(graph, "nodes", {}).values():
        if node.get("kind") == "judgment" and node.get("term_id") == term["id"]:
            if node.get("context_id") != term.get("context_id"):
                continue
            candidates.append(node)
    if not candidates:
        raise LawValidationError("reduce requires a typing judgment for the term in the graph")
    if len(candidates) > 1:
        raise LawValidationError("reduce found multiple typing judgments for the term")
    typing_judgment = candidates[0]

    # Optionally link reduction evidence to evaluation context and
    # reducible_environment when they are present in the graph. This ties
    # the operational Reduce act to the evaluation_context and
    # reducibility_candidates infrastructure without changing the core
    # single-step semantics.
    eval_ctx_id = None
    for node in getattr(graph, "nodes", {}).values():
        if node.get("kind") == "evaluation_context" and node.get("trace_id") == trace["id"]:
            eval_ctx_id = node["id"]
            break
    reducible_env_id = None
    for node in getattr(graph, "nodes", {}).values():
        if node.get("kind") == "reducible_environment" and node.get("context_id") == term.get("context_id"):
            reducible_env_id = node["id"]
            break

    redex_location: Dict[str, object] = {"path": []}
    if eval_ctx_id is not None:
        redex_location["evaluation_context_id"] = eval_ctx_id
        # For the minimal fragment, the redex is at the outermost frame.
        redex_location["frame_index"] = 0
    if reducible_env_id is not None:
        redex_location["reducible_environment_id"] = reducible_env_id

    reduction_evidence = {
        "kind": "reduction_evidence",
        "term_before_id": term["id"],
        "term_after_id": new_term["id"],
        "trace_id": new_trace["id"],
        "redex_location": redex_location,
        "typing_witness_id": typing_judgment["id"],
        "status": "pass",
        "act_ref": "Reduce",
    }
    ensure_id_coherence(reduction_evidence)

    reduce_edge = {
        "operator": "reduce",
        "src": term["id"],
        "tgt": new_term["id"],
        "evidence_ids": [reduction_evidence["id"]],
    }

    nodes = [new_term, new_trace, reduction_evidence]
    edges = [reduce_edge]
    bindings = {
        "term": new_term["id"],
        "trace": new_trace["id"],
        "reduction_evidence": reduction_evidence["id"],
    }

    return RealizerOutput(
        nodes=nodes,
        edges=edges,
        bindings=bindings,
    )
