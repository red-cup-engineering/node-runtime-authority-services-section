from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    context_geometry realizer.

    Inputs
    ------
    presheaf_site:
        Site carrier (kind ``presheaf_site``) describing contexts, arrows,
        and covers.

    Semantics
    ---------
    Realizes the ContextGeometry act by packaging a context_geometry carrier
    that records the site ID and a geometry summary derived from its objects
    and covers.
    """
    site = inputs.get("presheaf_site")
    if site is None:
        raise KeyError("context_geometry requires 'presheaf_site' input")
    if site.get("kind") != "presheaf_site":
        raise LawValidationError("context_geometry input must have kind 'presheaf_site'")

    geometry = {
        "objects": list(site.get("objects", [])),
        "covers": list(site.get("covers", [])),
    }
    payload = {
        "kind": "context_geometry",
        "site_id": site["id"],
        "geometry": geometry,
        "act_ref": "ContextGeometry",
    }
    ensure_id_coherence(payload)

    edge = {
        "operator": "context_geometry",
        "src": site["id"],
        "tgt": payload["id"],
    }

    return RealizerOutput(
        nodes=[payload],
        edges=[edge],
        bindings={"context_geometry": payload["id"]},
    )

