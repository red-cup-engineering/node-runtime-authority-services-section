from __future__ import annotations

from typing import Iterable, Set

from ..sscu_model import UniverseInstance


def published_representatives(
    instance: UniverseInstance,
    publish_to: Iterable[str] | None = None,
    statuses: Iterable[str] | None = None,
) -> Set[str]:
    publish_targets = {p.lower() for p in publish_to} if publish_to else set()
    status_targets = {s.lower() for s in statuses} if statuses else set()

    def _matches(rep: str) -> bool:
        concept = instance.canonical_concepts[rep]
        if concept.publish is False:
            return False
        concept_status = (concept.status or "").lower()
        concept_targets = {p.lower() for p in concept.publish_to or []}
        if isinstance(concept.publish, list):
            concept_targets.update(str(p).lower() for p in concept.publish)

        if status_targets and concept_status not in status_targets:
            return False
        if publish_targets:
            if not concept_targets:
                return False
            if not (concept_targets & publish_targets):
                return False
        return True

    return {rep for rep in instance.canonical_concepts if _matches(rep)}
