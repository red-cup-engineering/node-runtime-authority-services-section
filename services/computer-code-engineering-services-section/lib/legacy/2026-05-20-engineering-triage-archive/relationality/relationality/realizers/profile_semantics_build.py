from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_semantics_build realizer.

    Inputs
    ------
    profile_topos:
        ProfileTopos carrier encoding the finite judgment lattice with
        subobject classifier and finite limits.
    judgment_laws_evidence:
        JudgmentLawsEvidence node witnessing that the lattice laws hold on the
        profile_topos carrier.
    profile_semantics_evidence:
        ProfileSemanticsEvidence node witnessing classifier/limits coherence
        for the same profile_topos.

    Semantics
    ---------
    Realizes ProfileSemantics = (StructureSemantics ProfileRecognitions) by
    packaging the classifier/limits data of the profile and the associated
    witnesses into an explicit profile_semantics carrier:

        classifier_data = profile_topos.subobject_classifier
        limits_data = profile_topos.finite_limits
        witness_ids = {judgment_laws_evidence.id,
                       profile_semantics_evidence.id}

    The build requires both evidences to have status == 'pass' and to be
    attached to the supplied profile_topos.
    """
    profile = inputs.get("profile_topos")
    j_evd = inputs.get("judgment_laws_evidence")
    p_evd = inputs.get("profile_semantics_evidence")
    if profile is None or j_evd is None or p_evd is None:
        raise KeyError(
            "profile_semantics_build requires 'profile_topos', "
            "'judgment_laws_evidence', and 'profile_semantics_evidence' inputs"
        )

    if profile.get("kind") != "profile_topos":
        raise LawValidationError("profile_semantics_build profile_topos input must have kind 'profile_topos'")
    if j_evd.get("kind") != "judgment_laws_evidence":
        raise LawValidationError("profile_semantics_build judgment_laws_evidence input must have kind 'judgment_laws_evidence'")
    if p_evd.get("kind") != "profile_semantics_evidence":
        raise LawValidationError(
            "profile_semantics_build profile_semantics_evidence input must have kind 'profile_semantics_evidence'"
        )

    profile_id = profile["id"]
    if j_evd.get("carrier_id") != profile_id:
        raise LawValidationError(
            "profile_semantics_build requires judgment_laws_evidence.carrier_id to match profile_topos.id"
        )
    if p_evd.get("profile_topos_id") != profile_id:
        raise LawValidationError(
            "profile_semantics_build requires profile_semantics_evidence.profile_topos_id to match profile_topos.id"
        )
    if j_evd.get("status") != "pass":
        raise LawValidationError("profile_semantics_build requires judgment_laws_evidence.status == 'pass'")
    if p_evd.get("status") != "pass":
        raise LawValidationError("profile_semantics_build requires profile_semantics_evidence.status == 'pass'")

    classifier = profile.get("subobject_classifier") or {}
    finite_limits = profile.get("finite_limits") or {}

    payload = {
        "kind": "profile_semantics",
        "profile_topos_id": profile_id,
        "classifier_data": classifier,
        "limits_data": finite_limits,
        "witness_ids": [
            j_evd["id"],
            p_evd["id"],
        ],
    }
    ensure_id_coherence(payload)

    edges = [
        {
            "operator": "profile_semantics_build",
            "src": profile_id,
            "tgt": payload["id"],
        },
        {
            "operator": "profile_semantics_build",
            "src": j_evd["id"],
            "tgt": payload["id"],
        },
        {
            "operator": "profile_semantics_build",
            "src": p_evd["id"],
            "tgt": payload["id"],
        },
    ]

    return RealizerOutput(
        nodes=[payload],
        edges=edges,
        bindings={"profile_semantics": payload["id"]},
    )

