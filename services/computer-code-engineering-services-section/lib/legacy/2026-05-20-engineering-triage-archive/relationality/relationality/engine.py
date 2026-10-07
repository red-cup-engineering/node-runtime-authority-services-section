"""
Runbook execution engine and realizer contract.

Realizers are pure functions of the form::

    realize(graph, inputs, context) -> RealizerOutput

``inputs`` is a mapping from role -> payload (canonical JSON objects).
``context`` includes the runbook payload and step metadata.
Realizers must not mutate the graph; the engine applies mutations atomically
after validation succeeds.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Dict, Mapping, MutableMapping

from .graph import RelationalGraph
from .validation import validate_object
from .canonical import ensure_id_coherence
from .realizers import resolve_realizer
from .law_enforcement import validate_raw_object, validate_raw_runbook


@dataclass
class RealizerOutput:
    nodes: list[dict]
    edges: list[dict]
    bindings: dict[str, str]


def _prepare_nodes(nodes: list[MutableMapping[str, object]]) -> dict[str, dict]:
    prepared: dict[str, dict] = {}
    for node in nodes:
        # Use the shared law-enforcement channel for carrier validation.
        validate_raw_object(node)
        node_id = node["id"]
        if node_id in prepared and prepared[node_id] != node:
            raise ValueError(f"duplicate node id {node_id} with conflicting payload")
        prepared[node_id] = dict(node)
    return prepared


def _prepare_edges(edges: list[MutableMapping[str, object]], runbook_id: str, step_index: int) -> dict[str, dict]:
    prepared: dict[str, dict] = {}
    for edge in edges:
        edge = dict(edge)
        edge["runbook_id"] = runbook_id
        edge["step_index"] = step_index
        ensure_id_coherence(edge)
        edge_id = edge["id"]
        if edge_id in prepared and prepared[edge_id] != edge:
            raise ValueError(f"duplicate edge id {edge_id} with conflicting payload")
        prepared[edge_id] = edge
    return prepared


def execute_runbook(graph: RelationalGraph, runbook: Mapping[str, object], initial_bindings: dict[str, str]) -> dict[str, str]:
    """
    Execute a runbook against the given graph.

    ``initial_bindings`` maps runbook-level input roles to node IDs already
    present in the graph.
    """
    # Canonicalize and validate the runbook structure via the shared
    # law-enforcement channel. Operator→realizer coverage is enforced at
    # boot/runtime level, not per-execution.
    validate_raw_runbook(copy.deepcopy(runbook))
    bindings = dict(initial_bindings)
    # Validate initial bindings match declared inputs.
    declared_inputs = runbook.get("inputs", [])
    for item in declared_inputs:
        role, expected_kind = item["role"], item["kind"]
        if role not in bindings:
            raise KeyError(f"missing binding for input role {role}")
        node_id = bindings[role]
        if node_id not in graph.nodes:
            raise KeyError(f"binding for role {role} references unknown node {node_id}")
        if graph.nodes[node_id]["kind"] != expected_kind:
            raise ValueError(f"binding for role {role} has kind {graph.nodes[node_id]['kind']} but expected {expected_kind}")
    for step in sorted(runbook["steps"], key=lambda s: s["step_index"]):
        _execute_step(graph, runbook, step, bindings)
    return bindings


def _execute_step(graph: RelationalGraph, runbook: Mapping[str, object], step: Mapping[str, object], bindings: dict[str, str]) -> None:
    # Resolve inputs.
    inputs: dict[str, dict] = {}
    for spec in step.get("inputs", []):
        role = spec["role"]
        expected_kind = spec["kind"]
        node_id = bindings.get(role)
        if node_id is None:
            raise KeyError(f"step {step['step_index']} missing binding for role {role}")
        node = graph.nodes.get(node_id)
        if node is None:
            raise KeyError(f"step {step['step_index']} binding {node_id} not found in graph")
        if node["kind"] != expected_kind:
            raise ValueError(f"step {step['step_index']} binding {role} has kind {node['kind']} expected {expected_kind}")
        inputs[role] = node
    realizer = resolve_realizer(step["operator"])
    output: RealizerOutput = realizer(
        graph=graph,
        inputs=inputs,
        context={
            "runbook": runbook,
            "step": step,
        },
    )
    new_nodes = _prepare_nodes([dict(n) for n in output.nodes])
    candidate_nodes = {**graph.nodes, **new_nodes}
    new_edges = _prepare_edges([dict(e) for e in output.edges], runbook["id"], step["step_index"])
    # Edge endpoint validation
    for edge in new_edges.values():
        if edge["src"] not in candidate_nodes:
            raise ValueError(f"edge {edge['id']} references unknown src {edge['src']}")
        if edge["tgt"] not in candidate_nodes:
            raise ValueError(f"edge {edge['id']} references unknown tgt {edge['tgt']}")
        if edge["operator"] != step["operator"]:
            raise ValueError(f"edge {edge['id']} operator {edge['operator']} does not match step operator {step['operator']}")
    # Output binding validation.
    expected_outputs = {spec["role"]: spec["kind"] for spec in step.get("outputs", [])}
    for role, node_id in output.bindings.items():
        if node_id not in candidate_nodes:
            raise ValueError(f"binding for role {role} references unknown node {node_id}")
        if role in expected_outputs:
            expected_kind = expected_outputs[role]
            if candidate_nodes[node_id]["kind"] != expected_kind:
                raise ValueError(f"binding {role} has kind {candidate_nodes[node_id]['kind']} expected {expected_kind}")
    if set(expected_outputs.keys()) - set(output.bindings.keys()):
        missing = set(expected_outputs.keys()) - set(output.bindings.keys())
        raise ValueError(f"step {step['step_index']} missing bindings for roles {sorted(missing)}")
    # Mutate graph only after all validations succeed.
    for node in new_nodes.values():
        graph.add_node(node)
    for edge in new_edges.values():
        graph.add_edge(edge)
    bindings.update(output.bindings)
