from __future__ import annotations

from typing import Dict, List, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _typed_terms_for_profile(
    graph,
    profile_topos_id: str,
) -> tuple[List[str], List[str]]:
    """
    Collect term and judgment IDs whose judgments live over the given profile.

    We interpret JudgeTyping witnessing ProfileSemantics as selecting those
    judgment carriers whose types are elements of the profile_topos lattice.
    Concretely, we scan existing judgment objects in the graph and retain
    those whose type_id is an element of the profile lattice (when that
    lattice is explicitly enumerated).
    """
    nodes: Mapping[str, dict] = getattr(graph, "nodes", {})
    profile = nodes.get(profile_topos_id)
    if profile is None or profile.get("kind") != "profile_topos":
        raise LawValidationError("calculate_profile_syntax: profile_topos_id must reference a profile_topos node")
    profile_elements = set(profile.get("elements", []))
    term_ids: List[str] = []
    judgment_ids: List[str] = []
    for node_id, node in nodes.items():
        if node.get("kind") != "judgment":
            continue
        type_id = node.get("type_id")
        if type_id is None:
            continue
        # Restrict to judgments whose type lies in the profile lattice.
        if type_id in profile_elements:
            judgment_ids.append(node_id)
            term_id = node.get("term_id")
            if isinstance(term_id, str):
                term_ids.append(term_id)
    # Deduplicate while preserving order.
    seen_terms: set[str] = set()
    unique_terms: List[str] = []
    for tid in term_ids:
        if tid not in seen_terms:
            seen_terms.add(tid)
            unique_terms.append(tid)
    return unique_terms, judgment_ids


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    calculate_profile_syntax realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier providing the profile lattice.
    profile_semantics:
        ProfileSemantics carrier packaging classifier/limits/witnesses for
        the same profile_topos.

    Semantics
    ---------
    Acts: CalculateProfileSyntax = (JudgeTyping ProfileSemantics).

    We realize this by selecting the subset of term/judgment carriers whose
    typing judgments live over the given profile lattice and packaging them
    into a profile_syntax carrier:

        profile_topos_id = profile_topos.id
        profile_semantics_id = profile_semantics.id
        term_ids = { term_id | ∃ judgment with term_id and type_id ∈ profile.elements }
        judgment_ids = IDs of those judgments.
    """
    profile_topos = inputs.get("profile_topos")
    profile_semantics = inputs.get("profile_semantics")
    if profile_topos is None or profile_semantics is None:
        raise KeyError("calculate_profile_syntax requires 'profile_topos' and 'profile_semantics' inputs")
    if profile_topos.get("kind") != "profile_topos":
        raise LawValidationError("calculate_profile_syntax profile_topos input must have kind 'profile_topos'")
    if profile_semantics.get("kind") != "profile_semantics":
        raise LawValidationError("calculate_profile_syntax profile_semantics input must have kind 'profile_semantics'")
    if profile_semantics.get("profile_topos_id") != profile_topos["id"]:
        raise LawValidationError(
            "calculate_profile_syntax requires profile_semantics.profile_topos_id to match profile_topos.id"
        )

    term_ids, judgment_ids = _typed_terms_for_profile(graph, profile_topos["id"])

    payload = {
        "kind": "profile_syntax",
        "profile_topos_id": profile_topos["id"],
        "profile_semantics_id": profile_semantics["id"],
        "term_ids": term_ids,
        "judgment_ids": judgment_ids,
        "act_ref": "CalculateProfileSyntax",
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "calculate_profile_syntax",
            "src": profile_topos["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "calculate_profile_syntax",
            "src": profile_semantics["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"profile_syntax": payload["id"]},
    )

