"""
Invocation harness for runbook-driven realizer execution.

This module provides a small helper that:
- resolves a named runbook from the persisted runbook index;
- loads the required input carriers from the object index;
- constructs a minimal RelationalGraph containing those carriers; and
- executes the runbook via the engine, returning the updated graph and
  binding environment.

The goal is to keep all operator execution runbook-driven rather than
ad-hoc per-realizer call patterns.
"""

from __future__ import annotations

from typing import Dict, Mapping, Tuple

from .engine import execute_runbook
from .graph import RelationalGraph
from .runtime import get_computer
from .validation import LawValidationError


def execute_realizer(
    runbook_name: str,
    initial_bindings: Mapping[str, str],
) -> Tuple[RelationalGraph, Dict[str, str]]:
    """
    Execute a named runbook against persisted carriers.

    Parameters
    ----------
    runbook_name:
        Name of the runbook to execute (as declared in the runbook schema
        and persisted runbook files).
    initial_bindings:
        Mapping from runbook-level input roles to carrier IDs already
        present in the object store.

    Returns
    -------
    graph, bindings:
        The RelationalGraph after execution (containing all input carriers
        and any nodes/edges emitted by the runbook), and the final binding
        environment produced by ``execute_runbook``.

    Raises
    ------
    KeyError, LawValidationError, ValueError
        If required runbooks or objects are missing, or if kinds/bindings
        violate the runbook's typing constraints.
    """
    computer = get_computer(require_runtime_viability=True)
    objects_index = computer.objects
    runbooks_index = computer.runbooks

    rb_map = runbooks_index.by_name.get(runbook_name) or {}
    if not rb_map:
        raise KeyError(f"no persisted runbook found with name {runbook_name!r}")
    # When multiple runbooks share the same name, choose the one with the
    # lexicographically minimal ID to keep invocation deterministic.
    runbook_id = sorted(rb_map.keys())[0]
    runbook = rb_map[runbook_id]

    graph = RelationalGraph()

    # Seed the graph with all carriers named in initial_bindings, checking
    # both existence and kind alignment against the runbook's declared inputs.
    declared_inputs = runbook.get("inputs", []) or []
    for spec in declared_inputs:
        role = spec["role"]
        expected_kind = spec["kind"]
        node_id = initial_bindings.get(role)
        if node_id is None:
            raise KeyError(f"missing binding for input role {role!r} for runbook {runbook_name!r}")
        payload = objects_index.by_id.get(node_id)
        if payload is None:
            raise KeyError(f"binding for role {role!r} references unknown object id {node_id}")
        if payload.get("kind") != expected_kind:
            raise LawValidationError(
                f"binding for role {role!r} has kind {payload.get('kind')} but expected {expected_kind}"
            )
        graph.add_node(dict(payload))

    final_bindings = execute_runbook(graph, runbook, dict(initial_bindings))
    return graph, final_bindings


__all__ = ["execute_realizer"]
