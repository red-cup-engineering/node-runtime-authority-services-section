from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .sscu_model import UniverseInstance


@dataclass
class DeltaSummary:
    """Summarize changes between two evaluated SSCU instances."""

    ann_changes: Dict[str, str]
    reference_changes: Dict[str, str]
    failures_added: List[str]
    failures_removed: List[str]
    unresolved_added: List[Tuple[str, str]]
    unresolved_removed: List[Tuple[str, str]]
    baseline_present: bool


def _ann_snapshot(instance: UniverseInstance) -> Dict[str, List[str]]:
    return {rep: [term.surface() for term in concept.ann] for rep, concept in instance.canonical_concepts.items()}


def _references_snapshot(instance: UniverseInstance) -> Dict[str, List[str]]:
    return {rep: sorted(targets) for rep, targets in instance.reference_graph.items()}


def compute_delta(prev: UniverseInstance | None, current: UniverseInstance) -> DeltaSummary:
    prev_ann = _ann_snapshot(prev) if prev else {}
    curr_ann = _ann_snapshot(current)
    ann_changes: Dict[str, str] = {}
    for const in sorted(set(prev_ann) | set(curr_ann)):
        if const not in prev_ann:
            ann_changes[const] = "added"
        elif const not in curr_ann:
            ann_changes[const] = "removed"
        elif prev_ann[const] != curr_ann[const]:
            ann_changes[const] = "changed"

    prev_refs = _references_snapshot(prev) if prev else {}
    curr_refs = _references_snapshot(current)
    reference_changes: Dict[str, str] = {}
    for const in sorted(set(prev_refs) | set(curr_refs)):
        if const not in prev_refs:
            reference_changes[const] = "added"
        elif const not in curr_refs:
            reference_changes[const] = "removed"
        elif prev_refs[const] != curr_refs[const]:
            reference_changes[const] = "changed"

    prev_failures = set(map(repr, prev.failures)) if prev else set()
    curr_failures = set(map(repr, current.failures))
    failures_added = sorted(curr_failures - prev_failures)
    failures_removed = sorted(prev_failures - curr_failures)

    prev_unresolved = set(prev.unresolved) if prev else set()
    curr_unresolved = set(current.unresolved)
    unresolved_added = sorted(curr_unresolved - prev_unresolved)
    unresolved_removed = sorted(prev_unresolved - curr_unresolved)

    return DeltaSummary(
        ann_changes=ann_changes,
        reference_changes=reference_changes,
        failures_added=failures_added,
        failures_removed=failures_removed,
        unresolved_added=unresolved_added,
        unresolved_removed=unresolved_removed,
        baseline_present=prev is not None,
    )


def delta_to_dict(delta: DeltaSummary) -> Dict:
    return {
        "ann_changes": delta.ann_changes,
        "reference_changes": delta.reference_changes,
        "failures": {"added": delta.failures_added, "removed": delta.failures_removed},
        "unresolved": {"added": delta.unresolved_added, "removed": delta.unresolved_removed},
        "baseline_present": delta.baseline_present,
    }
