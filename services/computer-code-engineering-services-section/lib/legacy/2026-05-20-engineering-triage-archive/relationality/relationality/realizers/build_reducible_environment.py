from __future__ import annotations

from typing import Dict, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    build_reducible_environment realizer.

    Inputs
    ------
    context:
        TermContext carrier (kind ``term_context``) listing variables.
    reducibility_candidates:
        ReducibilityCandidates carrier (kind ``reducibility_candidates``)
        mapping variables to candidate terms and witnesses.

    Semantics
    ---------
    Build a reducible_environment carrier whose bindings are the candidates
    restricted to the context variables, requiring total coverage:
    - every variable in context.variables must appear in candidates;
    - bindings contain exactly those variables.
    """
    ctx = inputs.get("context")
    candidates = inputs.get("reducibility_candidates")
    if ctx is None or candidates is None:
        raise KeyError("build_reducible_environment requires 'context' and 'reducibility_candidates' inputs")
    if ctx.get("kind") != "term_context":
        raise LawValidationError("build_reducible_environment context input must have kind 'term_context'")
    if candidates.get("kind") != "reducibility_candidates":
        raise LawValidationError("build_reducible_environment reducibility_candidates input must have kind 'reducibility_candidates'")

    context_id = ctx["id"]
    if candidates.get("context_id") != context_id:
        raise LawValidationError("reducibility_candidates.context_id must match context.id")

    vars_ctx = list(ctx.get("variables", []))
    cand_map: Mapping[str, dict] = candidates.get("candidates") or {}
    missing = [v for v in vars_ctx if v not in cand_map]
    if missing:
        raise LawValidationError(
            f"reducibility_candidates missing entries for context variables {sorted(missing)}"
        )

    bindings = {var: cand_map[var] for var in vars_ctx}
    env = {
        "kind": "reducible_environment",
        "context_id": context_id,
        "bindings": bindings,
    }
    ensure_id_coherence(env)

    edge = {
        "operator": "build_reducible_environment",
        "src": context_id,
        "tgt": env["id"],
    }

    return RealizerOutput(
        nodes=[env],
        edges=[edge],
        bindings={"reducible_environment": env["id"]},
    )

