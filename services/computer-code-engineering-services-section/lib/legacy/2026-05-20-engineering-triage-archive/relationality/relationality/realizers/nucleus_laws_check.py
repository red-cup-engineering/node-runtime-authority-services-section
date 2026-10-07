from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.nucleus_algebra import nucleus_law_checks, resolve_nucleus_carrier
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    nucleus_laws_check realizer.

    Input
    -----
    nucleus_map:
        Carrier encoding a nucleus table ν:R→R over a finite lattice carrier.

    Semantics
    ---------
    Evaluate the nucleus laws over the finite carrier:
    - extensive:        x <= ν(x)
    - idempotent:       ν(ν(x)) = ν(x)
    - monotone:         x <= y ⇒ ν(x) <= ν(y)
    - equalize:         ν(x ∧ ν(y)) = ν(x ∧ y) and ν(ν(x) ∨ y) = ν(x ∨ y)
    - absorb:           x ∧ ν(y) <= ν(x ∧ y)

    Produce a nucleus_laws_evidence node recording per-law booleans and the
    first counterexample (if any). This is diagnostic: law failures do not
    raise, but are encoded in the evidence.
    """
    nucleus_map = inputs.get("nucleus_map")
    if nucleus_map is None:
        raise KeyError("nucleus_laws_check requires nucleus_map input")
    if nucleus_map.get("kind") != "nucleus_map":
        raise LawValidationError("nucleus_laws_check nucleus_map input must have kind 'nucleus_map'")

    carrier = resolve_nucleus_carrier(graph, nucleus_map)
    checks, counterexample = nucleus_law_checks(carrier, nucleus_map)

    status = "pass" if all(checks.values()) else "fail"

    evidence = {
        "kind": "nucleus_laws_evidence",
        "nucleus_id": nucleus_map["id"],
        "carrier_id": carrier["id"],
        "checks": checks,
        "status": status,
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edges = [
        {
            "operator": "nucleus_laws_check",
            "src": nucleus_map["id"],
            "tgt": evidence["id"],
        },
        {
            "operator": "nucleus_laws_check",
            "src": carrier["id"],
            "tgt": evidence["id"],
        },
    ]

    return RealizerOutput(
        nodes=[evidence],
        edges=edges,
        bindings={"nucleus_laws_evidence": evidence["id"]},
    )
