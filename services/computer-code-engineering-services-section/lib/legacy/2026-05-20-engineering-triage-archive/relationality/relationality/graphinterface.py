"""
Typed AOG interface aligned to acts/README:
- Nodes are recognition objects (id/kind/acts/payload/metadata).
- Edges are typed operators (operator/runbook/realizer) producing new nodes.
- Operator templates come from runbooks and serve as the graph's type system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from relationality.graph import AOG, NodeData, EdgeData


@dataclass
class OperatorStep:
    operator: str
    input_kind: str
    output_kind: str
    runbook_id: str
    realizer_id: str


def add_recognition(graph: AOG, node_id: str, kind: str, acts: List[str], payload: Dict[str, Any], metadata: Dict[str, Any] | None = None, status: str = "loaded") -> None:
    graph.add_node(
        NodeData(
            id=node_id,
            kind=kind,
            acts=acts,
            payload=payload,
            metadata=metadata or {},
        ),
        status=status,
    )


def add_operator_edge(graph: AOG, source_id: str, target: NodeData, step: OperatorStep, diagnostics: Optional[Dict[str, Any]] = None) -> None:
    graph.add_edge(
        source_id,
        target,
        EdgeData(
            operator=step.operator,
            runbook_id=step.runbook_id,
            realizer_id=step.realizer_id,
            diagnostics=diagnostics or {},
        ),
    )


def record_template(graph: AOG, step: OperatorStep) -> None:
    graph.record_operator_template(
        input_kind=step.input_kind,
        output_kind=step.output_kind,
        operator=step.operator,
        runbook_id=step.runbook_id,
        realizer_id=step.realizer_id,
    )


def get_node(graph: AOG, node_id: str) -> NodeData:
    return graph.get_node(node_id)


def find_by_kind(graph: AOG, kind: str) -> List[str]:
    return graph.find_by_kind(kind)


def apply_step(
    graph: AOG,
    source_id: str,
    step: OperatorStep,
    realizer_fn,
    diagnostics: Optional[Dict[str, Any]] = None,
) -> Tuple[NodeData, Dict[str, Any]]:
    """Apply a single operator step to the source node, returning the new node and merged diagnostics."""
    current = graph.get_node(source_id)
    if current.kind != step.input_kind:
        raise TypeError(f"Step {step.operator} expected kind {step.input_kind} but got {current.kind}")
    context_diag = dict(diagnostics or {})
    result = realizer_fn(current, context_diag)
    if not isinstance(result, dict):
        raise TypeError("Realizer must return a mapping with kind/payload.")
    if result.get("kind") != step.output_kind:
        raise TypeError(f"Realizer returned kind {result.get('kind')} expected {step.output_kind}")
    target = NodeData(
        id=result.get("id") or f"{step.operator}:{source_id}",
        kind=result["kind"],
        acts=result.get("acts", []),
        payload=result.get("payload", {}),
        metadata=result.get("metadata", {}),
    )
    merged_diag = {"operators_used": [step.operator]}
    merged_diag.update(context_diag)
    add_operator_edge(graph, source_id, target, step, diagnostics=context_diag)
    return target, merged_diag
