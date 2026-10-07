"""
Local, ephemeral AOG views and runbook execution.

This module provides a minimal graph-like container and a deterministic
runbook executor that operate on a finite, in-memory view built on
request from persisted carriers and optional external inputs.

It deliberately does **not** depend on the legacy ``RelationalGraph``
or the global engine: callers construct a ``LocalGraph`` for the
neighbourhood they care about, execute a runbook, and then discard the
resulting view.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, MutableMapping

from .canonical import ensure_id_coherence
from .realizers import resolve_realizer
from .validation import LawValidationError, validate_object, validate_runbook


@dataclass
class LocalGraph:
    """
    Minimal, local AOG view.

    ``nodes`` maps canonical IDs to carrier payloads.
    ``edges`` maps canonical IDs to edge payloads.

    The container is intentionally kept simple: realizers only require
    read-only access to ``graph.nodes`` to discover ambient carriers.
    """

    nodes: Dict[str, dict] = field(default_factory=dict)
    edges: Dict[str, dict] = field(default_factory=dict)


def validate_raw_object(payload: MutableMapping[str, object]) -> None:
    """
    Full validation pipeline for a raw carrier payload in a local view.

    This mirrors the object-side of the legacy engine:
    - assign/overwrite ``id`` using :func:`ensure_id_coherence`;
    - enforce schema + carrier-local laws via :func:`validate_object`.
    """
    ensure_id_coherence(payload)
    validate_object(payload)


def _prepare_nodes(nodes: list[MutableMapping[str, object]]) -> Dict[str, dict]:
    """
    Validate and canonicalize a batch of node payloads.

    Returns a mapping id -> payload ready to be merged into a LocalGraph.
    """
    prepared: Dict[str, dict] = {}
    for node in nodes:
        data = dict(node)
        validate_raw_object(data)
        node_id = data["id"]
        existing = prepared.get(node_id)
        if existing is not None and existing != data:
            raise ValueError(f"duplicate node id {node_id} with conflicting payload in local execution")
        prepared[node_id] = data
    return prepared


def _prepare_edges(
    edges: list[MutableMapping[str, object]],
    runbook_id: str,
    step_index: int,
) -> Dict[str, dict]:
    """
    Canonicalize a batch of edge payloads.

    Each edge is augmented with ``runbook_id`` and ``step_index`` and
    assigned a canonical ``id`` via :func:`ensure_id_coherence`.
    """
    prepared: Dict[str, dict] = {}
    for edge in edges:
        data = dict(edge)
        data["runbook_id"] = runbook_id
        data["step_index"] = step_index
        ensure_id_coherence(data)
        edge_id = data["id"]
        existing = prepared.get(edge_id)
        if existing is not None and existing != data:
            raise ValueError(f"duplicate edge id {edge_id} with conflicting payload in local execution")
        prepared[edge_id] = data
    return prepared


def execute_runbook_local(
    graph: LocalGraph,
    runbook: Mapping[str, object],
    initial_bindings: Mapping[str, str],
    *,
    validate_structure: bool = True,
) -> Dict[str, str]:
    """
    Execute a runbook against a local, finite ``LocalGraph`` view.

    ``initial_bindings`` maps runbook-level input roles to node IDs
    already present in ``graph.nodes``.

    This executor:
    - optionally validates the runbook structure and hash;
    - checks that initial bindings satisfy the declared input kinds;
    - runs steps in ``step_index`` order, resolving operators to
      realizers via :func:`resolve_realizer`;
    - validates and canonicalizes emitted nodes/edges; and
    - mutates the provided ``graph`` only after each step passes all
      checks.
    """
    if validate_structure:
        # Work on a shallow copy so callers can reuse the original payload.
        validate_runbook(dict(runbook))

    bindings: Dict[str, str] = dict(initial_bindings)

    # Validate initial bindings against declared runbook inputs.
    for item in runbook.get("inputs", []):
        role = item["role"]
        expected_kind = item["kind"]
        if role not in bindings:
            raise KeyError(f"missing binding for input role {role!r}")
        node_id = bindings[role]
        node = graph.nodes.get(node_id)
        if node is None:
            raise KeyError(f"binding for role {role!r} references unknown node {node_id!r}")
        if node.get("kind") != expected_kind:
            raise ValueError(
                f"binding for role {role!r} has kind {node.get('kind')!r} "
                f"but expected {expected_kind!r}"
            )

    steps = sorted(runbook.get("steps", []), key=lambda s: s["step_index"])
    for step in steps:
        _execute_step_local(graph, runbook, step, bindings)

    return bindings


def _execute_step_local(
    graph: LocalGraph,
    runbook: Mapping[str, object],
    step: Mapping[str, object],
    bindings: Dict[str, str],
) -> None:
    # Resolve step inputs from current bindings.
    inputs: Dict[str, dict] = {}
    for spec in step.get("inputs", []):
        role = spec["role"]
        expected_kind = spec["kind"]
        node_id = bindings.get(role)
        if node_id is None:
            raise KeyError(f"step {step['step_index']} missing binding for role {role!r}")
        node = graph.nodes.get(node_id)
        if node is None:
            raise KeyError(f"step {step['step_index']} binding {node_id!r} not found in local graph")
        if node.get("kind") != expected_kind:
            raise ValueError(
                f"step {step['step_index']} binding {role!r} has kind {node.get('kind')!r} "
                f"expected {expected_kind!r}"
            )
        inputs[role] = node

    realizer = resolve_realizer(step["operator"])
    output = realizer(
        graph=graph,
        inputs=inputs,
        context={"runbook": runbook, "step": step},
    )

    # Validate and canonicalize emitted nodes/edges before mutating graph.
    new_nodes = _prepare_nodes([dict(n) for n in output.nodes])
    candidate_nodes = {**graph.nodes, **new_nodes}
    new_edges = _prepare_edges([dict(e) for e in output.edges], runbook["id"], step["step_index"])

    # Edge endpoint / operator validation.
    for edge in new_edges.values():
        src = edge.get("src")
        tgt = edge.get("tgt")
        if src not in candidate_nodes:
            raise ValueError(f"edge {edge['id']} references unknown src {src!r}")
        if tgt not in candidate_nodes:
            raise ValueError(f"edge {edge['id']} references unknown tgt {tgt!r}")
        if edge.get("operator") != step["operator"]:
            raise ValueError(
                f"edge {edge['id']} operator {edge.get('operator')!r} "
                f"does not match step operator {step['operator']!r}"
            )

    # Output binding validation against declared step outputs.
    expected_outputs = {spec["role"]: spec["kind"] for spec in step.get("outputs", [])}
    for role, node_id in output.bindings.items():
        if node_id not in candidate_nodes:
            raise ValueError(f"binding for role {role!r} references unknown node {node_id!r}")
        if role in expected_outputs:
            expected_kind = expected_outputs[role]
            actual_kind = candidate_nodes[node_id].get("kind")
            if actual_kind != expected_kind:
                raise ValueError(
                    f"binding {role!r} has kind {actual_kind!r} expected {expected_kind!r}"
                )
    missing_roles = set(expected_outputs.keys()) - set(output.bindings.keys())
    if missing_roles:
        raise ValueError(
            f"step {step['step_index']} missing bindings for roles {sorted(missing_roles)}"
        )

    # Mutate the local graph only after all validations succeed.
    graph.nodes.update(new_nodes)
    graph.edges.update(new_edges)
    bindings.update(output.bindings)


__all__ = ["LocalGraph", "validate_raw_object", "execute_runbook_local"]

