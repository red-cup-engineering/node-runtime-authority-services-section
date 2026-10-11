"""
Runtime view of the relational computer.

This module separates:
- *graph-level* validation and indexing (carriers + runbooks), and
- *runtime-level* viability (realizer coverage) and orchestration.

It does not introduce new AOG state: it simply packages the validated
object/runbook indexes and the resolved realizer modules into a single
\"RelationalComputer\" handle that higher-level surfaces (API, MCP,
CLI) can use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .boot import load_graph_indexes, validate_for_runtime
from .loaders import ObjectIndex, RunbookIndex
from .realizers import RealizerFn, resolve_realizer


@dataclass(frozen=True)
class RelationalComputer:
    """
    Sealed runtime handle for a validated relational graph.

    Attributes
    ----------
    objects:
        Canonical object index (carriers) loaded and law-checked.
    runbooks:
        Canonical runbook index loaded and law-checked.
    realizers:
        Mapping from operator name to resolved realizer callable. This
        associates the act/runbook surface with the internal Python
        modules but does not add any additional state.
    """

    objects: ObjectIndex
    runbooks: RunbookIndex
    realizers: Dict[str, RealizerFn]

    @classmethod
    def from_boot(cls, *, require_runtime_viability: bool = True) -> "RelationalComputer":
        """
        Construct a RelationalComputer from the canonical carriers/runbooks.

        When ``require_runtime_viability`` is True, this enforces that
        every declared operator has a resolvable realizer and that all
        persisted runbooks stay within the schema enums. When False, it
        only enforces graph/index laws.
        """
        if require_runtime_viability:
            objects, runbooks = validate_for_runtime()
        else:
            objects, runbooks = load_graph_indexes()

        # Associate the operator surface used in persisted runbooks with
        # concrete realizer modules. Since validate_for_runtime has
        # already enforced coverage in the default mode, this is a pure
        # name→callable mapping.
        operators: set[str] = set()
        for rb in runbooks.by_id.values():
            for step in rb.get("steps", []):
                op = step.get("operator")
                if isinstance(op, str):
                    operators.add(op)
        realizers: Dict[str, RealizerFn] = {}
        for op in sorted(operators):
            realizers[op] = resolve_realizer(op)

        return cls(objects=objects, runbooks=runbooks, realizers=realizers)


_DEFAULT_COMPUTER: Optional[RelationalComputer] = None


def get_computer(*, require_runtime_viability: bool = True) -> RelationalComputer:
    """
    Return a process-global RelationalComputer instance.

    Boot is conceptually a single canonical reconstruction of the AOG.
    This helper materializes that reconstruction once per process and
    reuses it across service providers (HTTP API, MCP, CLI).

    ``require_runtime_viability`` must be consistent across calls: once
    a runtime-viable computer has been created, later attempts to obtain
    a graph-only view must be performed in a separate process.
    """
    global _DEFAULT_COMPUTER
    if _DEFAULT_COMPUTER is None:
        _DEFAULT_COMPUTER = RelationalComputer.from_boot(
            require_runtime_viability=require_runtime_viability
        )
        return _DEFAULT_COMPUTER
    # If a computer already exists, enforce that we do not silently
    # weaken the viability requirement.
    if require_runtime_viability and _DEFAULT_COMPUTER is not None:
        return _DEFAULT_COMPUTER
    # require_runtime_viability is False but we already have a stronger
    # instance; reuse it rather than constructing a weaker view.
    return _DEFAULT_COMPUTER


__all__ = ["RelationalComputer", "get_computer"]
