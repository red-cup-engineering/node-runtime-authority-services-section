"""Linear runbook execution engine."""

from __future__ import annotations

from typing import Dict, List, Optional

from relationality.canonical import assign_canonical_id, hash_without_keys
from relationality.errors import LoaderError, HashMismatchError, IDMismatchError
from relationality.graph import RelationalGraph, Node
from relationality.realizer_registry import resolve_all
from relationality.schemas import validate_object


def _fetch_inputs(graph: RelationalGraph, input_ids: List[str]) -> List[Node]:
    inputs = []
    for node_id in input_ids:
        if node_id is None:
            continue
        candidates = graph.get_nodes_by_id(node_id)
        if not candidates:
            raise LoaderError(f"Missing input node {node_id}")
        # Deterministic selection: if multiple kinds, raise for ambiguity.
        if len(candidates) > 1:
            raise LoaderError(f"Ambiguous node id {node_id}, multiple kinds present")
        inputs.append(next(iter(candidates.values())))
    return inputs


def _enforce_regime(graph: RelationalGraph, operator: str) -> None:
    """If a regime is present in the graph, enforce its allowed/suppressed sets."""
    # Law/evidence operators are exempt from regime gating.
    law_ops = {
        "flow_laws",
        "nucleus_laws",
        "commutation",
        "judgment_laws",
        "trace_laws",
        "normalize_judgment_equivalence",
        "normalize_observation_equivalence",
        "evaluate_judgment",
    }
    if operator in law_ops or operator.endswith("_evidence"):
        return
    regimes = [node for node in graph.nodes.values() if node.kind == "regime"]
    if not regimes:
        return
    if len(regimes) > 1:
        raise LoaderError("Multiple regime nodes present; ambiguous enforcement")
    regime = regimes[0].payload
    allowed = regime.get("allowed_operators") or []
    suppressed = regime.get("suppressed_operators") or []
    if suppressed and operator in suppressed:
        raise LoaderError(f"Operator {operator} is suppressed by regime {regime['id']}")
    if allowed and operator not in allowed:
        raise LoaderError(f"Operator {operator} not allowed by regime {regime['id']}")


def _validate_outputs(outputs: List[dict]) -> List[dict]:
    validated = []
    for payload in outputs:
        if "kind" not in payload:
            raise LoaderError("Output payload missing kind")
        canonical = assign_canonical_id(payload)
        if canonical["id"] != payload.get("id"):
            raise IDMismatchError(
                f"Output id {payload.get('id')} disagrees with canonical {canonical['id']}"
            )
        computed = hash_without_keys(payload)
        if computed != payload.get("id"):
            raise HashMismatchError(
                f"Output hash mismatch: expected {payload.get('id')} computed {computed}"
            )
        schema_name = f"{payload['kind'].replace('_', '-')}.schema.json"
        validate_object(payload, schema_name)
        validated.append(canonical)
    return validated


def execute_runbook(
    graph: RelationalGraph,
    runbook: dict,
    input_ids: List[str],
    step_bindings: Optional[Dict[int, List[str]]] = None,
) -> Dict[str, Node]:
    """Execute a runbook linearly, mutating the graph atomically per step.

    Returns a mapping of new/updated node ids to Node objects.
    """
    resolvers = resolve_all(runbook)
    current_inputs = input_ids
    results: Dict[str, Node] = {}

    for index, step in enumerate(runbook.get("steps", [])):
        op = step["operator"]
        step_index = step.get("step_index", index)
        if step_index != index:
            raise LoaderError(f"Step index mismatch: expected {index} found {step_index} for {op}")
        _enforce_regime(graph, op)
        realizer = resolvers[op]

        # Select inputs: either explicit ids on the step or current_inputs chaining.
        explicit_inputs = step.get("input_ids")
        bound_inputs = None
        if step_bindings is not None and index in step_bindings:
            bound_inputs = step_bindings[index]
        chosen_inputs = bound_inputs or explicit_inputs or current_inputs
        input_nodes = _fetch_inputs(graph, chosen_inputs)
        expected_input_kinds = step.get("input_kinds")
        if expected_input_kinds is not None:
            if len(expected_input_kinds) != len(input_nodes):
                raise LoaderError(
                    f"Step {index} expected {len(expected_input_kinds)} inputs, got {len(input_nodes)}"
                )
            for expected, node in zip(expected_input_kinds, input_nodes):
                if node.kind != expected:
                    raise LoaderError(
                        f"Step {index} expects kind {expected}, got {node.kind} for id {node.id}"
                    )
        # Realizer signature: run(graph, payloads, ctx) -> List[dict] payloads
        outputs = realizer(graph, [n.payload for n in input_nodes], ctx={})
        validated_outputs = _validate_outputs(outputs)

        expected_output_kinds = step.get("output_kinds")
        if expected_output_kinds is not None:
            if len(expected_output_kinds) != len(validated_outputs):
                raise LoaderError(
                    f"Step {index} expected {len(expected_output_kinds)} outputs, got {len(validated_outputs)}"
                )
            for expected, payload in zip(expected_output_kinds, validated_outputs):
                if payload["kind"] != expected:
                    raise LoaderError(
                        f"Step {index} expects output kind {expected}, got {payload['kind']}"
                    )

        edge_payloads = []
        for payload in validated_outputs:
            for inp in input_nodes or []:
                edge_payload = {
                    "operator": op,
                    "src": inp.id,
                    "tgt": payload["id"],
                    "runbook_id": runbook["id"],
                    "step_index": step_index,
                }
                edge_payload["id"] = hash_without_keys(edge_payload)
                edge_payloads.append(edge_payload)

        new_nodes: List[Node] = []
        inserted_edges = []
        try:
            for payload in validated_outputs:
                node = graph.add_node(payload)
                new_nodes.append(node)
                results[node.id] = node
            for edge_payload in edge_payloads:
                edge = graph.add_edge(edge_payload)
                inserted_edges.append(edge)
        except Exception:
            # Roll back any inserted nodes/edges to preserve atomicity of the step.
            for edge in inserted_edges:
                graph.edges.pop(edge.id, None)
            for node in new_nodes:
                key = (node.id, node.kind)
                graph.nodes.pop(key, None)
                if node.id in graph.nodes_by_id and node.kind in graph.nodes_by_id[node.id]:
                    graph.nodes_by_id[node.id].pop(node.kind, None)
                    if not graph.nodes_by_id[node.id]:
                        graph.nodes_by_id.pop(node.id, None)
            raise

        # Chain outputs to next step, preferring non-evidence kinds to avoid ambiguity.
        filtered = [node.id for node in new_nodes if not node.kind.endswith("_evidence")]
        current_inputs = filtered if filtered else [node.id for node in new_nodes]

    return results


def execute_runbook_by_id(
    graph: RelationalGraph,
    runbook_index: Dict[str, dict],
    runbook_id: str,
    input_ids: List[str],
    step_bindings: Optional[Dict[int, List[str]]] = None,
) -> Dict[str, Node]:
    """Lookup a runbook by id from the provided index and execute it."""
    if runbook_id not in runbook_index:
        raise LoaderError(f"Runbook id {runbook_id} not found")
    runbook = runbook_index[runbook_id]
    return execute_runbook(graph, runbook, input_ids, step_bindings=step_bindings)
