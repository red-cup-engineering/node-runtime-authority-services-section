from __future__ import annotations

from typing import Dict, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    sheaf_profile_consistency realizer.

    Inputs
    ------
    sheaf_or_presheaf:
        Sheaf or presheaf carrier (kind ``sheaf`` or ``presheaf``).
    profile_topos:
        ProfileTopos carrier.

    Semantics
    ---------
    Witnesses basic alignment between the sheaf/presheaf and the profile_topos
    by checking that:
    - the site has at least one object; and
    - the profile lattice has at least one element.
    """
    carrier = inputs.get("sheaf_or_presheaf")
    profile = inputs.get("profile_topos")
    if carrier is None or profile is None:
        raise KeyError("sheaf_profile_consistency requires 'sheaf_or_presheaf' and 'profile_topos' inputs")
    kind = carrier.get("kind")
    if kind not in {"sheaf", "presheaf"}:
        raise LawValidationError("sheaf_profile_consistency sheaf_or_presheaf input must have kind 'sheaf' or 'presheaf'")
    if profile.get("kind") != "profile_topos":
        raise LawValidationError("sheaf_profile_consistency profile_topos input must have kind 'profile_topos'")

    objects = carrier.get("objects") or []
    elements = profile.get("elements") or []
    checks: Mapping[str, bool] = {
        "nonempty_site": bool(objects),
        "nonempty_profile": bool(elements),
    }
    status = "pass" if all(checks.values()) else "fail"

    evidence = {
        "kind": "sheaf_profile_consistency_evidence",
        "profile_topos_id": profile["id"],
        "checks": dict(checks),
        "status": status,
        "act_ref": "SheafProfileConsistency",
    }
    if kind == "sheaf":
        evidence["sheaf_id"] = carrier["id"]
    else:
        evidence["presheaf_id"] = carrier["id"]
    ensure_id_coherence(evidence)

    edge = {
        "operator": "sheaf_profile_consistency",
        "src": carrier["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"sheaf_profile_consistency_evidence": evidence["id"]},
    )

