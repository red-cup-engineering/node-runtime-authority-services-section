"""
Boot-time helpers for the relational computer.

This module distinguishes between:

- *structural graph validation*: loading carriers and runbooks from
  disk, enforcing filename/id/hash coherence, schema correctness, and
  carrier-local laws via :mod:`relationality.loaders` /
  :mod:`relationality.validation`.
- *runtime viability*: additionally requiring that every operator
  declared in the runbook schema has a resolvable realizer module and
  that persisted runbooks use only those declared operators.

Boot-time helpers here intentionally **do not** enforce Flow/Nucleus/
System/geometry/runbook laws, which depend on AOG context; those are
handled by the runtime law layer via law-check runbooks.
"""

from __future__ import annotations

from typing import Tuple

from .law_enforcement import validate_realizer_coverage
from .loaders import ObjectIndex, RunbookIndex, load_objects, load_runbooks


def load_graph_indexes() -> Tuple[ObjectIndex, RunbookIndex]:
    """
    Load objects and runbooks, enforcing only graph/index laws.

    This is the entrypoint for tools that want to reason about the AOG
    as a mathematical object (e.g. law diagnostics, RDF projections)
    without requiring that every operator have an attached realizer
    module.
    """
    objects = load_objects()
    runbooks = load_runbooks()
    return objects, runbooks


def validate_for_runtime() -> Tuple[ObjectIndex, RunbookIndex]:
    """
    Load objects and runbooks and enforce runtime viability.

    In addition to the checks performed in :func:`load_graph_indexes`,
    this function:

    - requires that every operator declared in the runbook schema have
      a resolvable realizer module; and
    - requires that every persisted runbook use only operators and
      names declared in the schema.

    It raises :class:`relationality.validation.LawValidationError` if
    these conditions are not met.
    """
    objects, runbooks = load_graph_indexes()
    validate_realizer_coverage(objects.by_id, runbooks.by_id)
    return objects, runbooks


__all__ = ["load_graph_indexes", "validate_for_runtime"]
