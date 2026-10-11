from __future__ import annotations

from typing import Dict

from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_object


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    sheaf_condition realizer.

    Inputs
    ------
    presheaf:
        Presheaf carrier (kind ``presheaf``) whose site_id refers to a
        presheaf_site node already present in the graph.

    Semantics
    ---------
    Realizes the SheafCondition act by delegating to the
    sheafification_evidence realizer:

    - It resolves the presheaf_site from the graph via presheaf.site_id.
    - It invokes sheafification_evidence(graph, {presheaf_site, presheaf}, …)
      to compute matching families, glued sections, and uniqueness checks.
    - It returns the emitted sheafification_evidence node as the witness
      for SheafCondition, with an edge typed by the sheaf_condition operator.

    Any failure in the underlying sheafification_evidence realizer is
    propagated as a LawValidationError, and no nodes/edges are emitted.
    """
    presheaf = inputs.get("presheaf")
    if presheaf is None:
        raise KeyError("sheaf_condition requires 'presheaf' input")
    if presheaf.get("kind") != "presheaf":
        raise LawValidationError("sheaf_condition presheaf input must have kind 'presheaf'")

    site_id = presheaf.get("site_id")
    if not isinstance(site_id, str):
        raise LawValidationError("sheaf_condition requires presheaf.site_id to be a string")
    site = getattr(graph, "nodes", {}).get(site_id)
    if site is None:
        raise LawValidationError(f"presheaf_site {site_id!r} referenced by presheaf not found in graph")
    if site.get("kind") != "presheaf_site":
        raise LawValidationError("sheaf_condition requires presheaf.site_id to reference a presheaf_site")

    # Lazy import to avoid cycles and to reuse the existing SheafCondition
    # implementation in sheafification_evidence.
    from relationality.realizers.sheafification_evidence import (  # type: ignore[import]
        realize as sheafification_evidence_realizer,
    )

    output = sheafification_evidence_realizer(
        graph,
        {"presheaf_site": dict(site), "presheaf": dict(presheaf)},
        {
            "runbook": {
                "id": context.get("runbook", {}).get("id", "0" * 64),
                "name": "sheaf_condition",
            },
            "step": {"step_index": context.get("step", {}).get("step_index", 0)},
        },
    )
    if not output.nodes:
        raise LawValidationError("sheaf_condition: sheafification_evidence did not emit evidence node")
    evidence = output.nodes[0]
    validate_object(evidence)

    edge = {
        "operator": "sheaf_condition",
        "src": presheaf["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"sheafification_evidence": evidence["id"]},
    )

