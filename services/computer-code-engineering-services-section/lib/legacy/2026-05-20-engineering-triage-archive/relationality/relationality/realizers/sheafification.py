from __future__ import annotations

from typing import Dict, List

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    sheafification realizer.

    Inputs
    ------
    presheaf:
        Presheaf carrier (kind ``presheaf``).
    sheafification_evidence:
        Evidence carrier (kind ``sheafification_evidence``) produced by the
        sheaf_condition / sheafification_evidence realizer.

    Semantics
    ---------
    Constructs a sheaf carrier from the presheaf and its sheafification
    evidence by:
    - copying covers from the presheaf,
    - deriving gluing_families and glued_sections from the evidence.
    """
    presheaf = inputs.get("presheaf")
    evidence = inputs.get("sheafification_evidence")
    if presheaf is None or evidence is None:
        raise KeyError("sheafification requires 'presheaf' and 'sheafification_evidence' inputs")
    if presheaf.get("kind") != "presheaf":
        raise LawValidationError("sheafification presheaf input must have kind 'presheaf'")
    if evidence.get("kind") != "sheafification_evidence":
        raise LawValidationError("sheafification evidence input must have kind 'sheafification_evidence'")
    if evidence.get("presheaf_id") != presheaf["id"]:
        raise LawValidationError("sheafification_evidence.presheaf_id must match presheaf.id")

    covers = presheaf.get("covers", [])
    cover_objects: List[dict] = []
    for idx, cover in enumerate(covers):
        cover_objects.append(
            {
                "cover_id": f"cover_{idx}",
                "object": cover["object"],
                "arrows": list(cover.get("arrows", [])),
            }
        )

    glued_sections = evidence.get("glued_sections", {})
    gluing_families: List[dict] = []
    for key in sorted(glued_sections.keys()):
        gluing_families.append(
            {
                "cover_id": key,
                "sections": [],
            }
        )

    sheaf = {
        "kind": "sheaf",
        "presheaf_id": presheaf["id"],
        "covers": cover_objects,
        "gluing_families": gluing_families,
        "glued_sections": glued_sections,
        "uniqueness_witnesses": {},
    }
    ensure_id_coherence(sheaf)

    edge = {
        "operator": "sheafification",
        "src": presheaf["id"],
        "tgt": sheaf["id"],
    }

    return RealizerOutput(
        nodes=[sheaf],
        edges=[edge],
        bindings={"sheaf": sheaf["id"]},
    )

