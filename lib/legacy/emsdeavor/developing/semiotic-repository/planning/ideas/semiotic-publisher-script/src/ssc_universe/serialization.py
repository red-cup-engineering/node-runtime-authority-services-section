from __future__ import annotations

"""JSON-friendly serializers for SSCU evaluation artifacts."""

import datetime as _dt
from typing import Dict

from .annterm import ProvenanceHistory
from .sscu_model import Fragment, SemanticContribution, UniverseInstance


def _jsonable(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (_dt.datetime, _dt.date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    return str(obj)


def _serialize_provenance(history: ProvenanceHistory) -> list[dict]:
    return [
        {"kind": step.kind, "detail": step.detail, "inputs": list(step.inputs)}
        for step in history.steps
    ]


def _serialize_fragment(fragment: Fragment) -> dict:
    return {
        "generators": [
            {"value": repr(value), "provenance": _serialize_provenance(prov)}
            for value, prov in fragment.generators
        ],
        "elements": sorted(repr(el) for el in fragment.elements),
        "is_failure": fragment.is_failure,
        "provenance": {repr(elem): _serialize_provenance(prov) for elem, prov in fragment.provenance.items()},
    }


def _serialize_semantic(sem: SemanticContribution) -> dict:
    return {
        "fragment": _serialize_fragment(sem.fragment),
        "closure_trace": sem.closure_trace.steps,
    }


def serialize_instance(instance: UniverseInstance) -> Dict:
    """Render a UniverseInstance into a JSON-friendly mapping."""

    constants: Dict[str, dict] = {}
    canonical: Dict[str, dict] = {}
    for const, concept in instance.concepts.items():
        rep = instance.representative(const)
        constants[const] = {
            "id": const,
            "representative": rep,
            "title": concept.title,
            "tags": concept.tags,
            "ann": [term.surface() for term in concept.ann],
            "fragment": _serialize_fragment(instance.fragments[rep]),
            "sem": _serialize_semantic(instance.sem[rep]),
            "body": concept.body,
            "publish": concept.publish,
            "same_as": concept.same_as,
            "publish_to": concept.publish_to,
            "status": concept.status,
            "exogenous": _jsonable(getattr(concept, "exogenous", {})),
            "endogenous": _jsonable(getattr(concept, "endogenous", {})),
        }

    for rep, concept in instance.canonical_concepts.items():
        canonical[rep] = {
            "id": rep,
            "title": concept.title,
            "tags": concept.tags,
            "ann": [term.surface() for term in concept.ann],
            "fragment": _serialize_fragment(instance.fragments[rep]),
            "sem": _serialize_semantic(instance.sem[rep]),
            "body": concept.body,
            "publish": concept.publish,
            "same_as": concept.same_as,
            "equivalents": instance.equivalence_classes.get(rep, []),
            "publish_to": concept.publish_to,
            "status": concept.status,
            "exogenous": _jsonable(getattr(concept, "exogenous", {})),
            "endogenous": _jsonable(getattr(concept, "endogenous", {})),
        }

    return {
        "constants": constants,
        "canonical_constants": canonical,
        "equivalence_classes": instance.equivalence_classes,
        "groupoid": instance.groupoid_rep,
        "unresolved": instance.unresolved,
        "failures": sorted(repr(f) for f in instance.failures),
        "reference_graph": {k: sorted(v) for k, v in instance.reference_graph.items()},
        "config_hash": instance.config_hash,
        "repo_fingerprint": instance.repo_fingerprint,
        "sanitize_html": instance.sanitize_html,
        "html_lang": getattr(instance, "html_lang", "en"),
        "source_paths": getattr(instance, "source_paths", None),
    }
