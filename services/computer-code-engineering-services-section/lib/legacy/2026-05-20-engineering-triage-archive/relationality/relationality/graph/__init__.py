"""
Graph API for CRUD operations on the in-memory Aperiodic Operator Graph (AOG).

This module will serve as the single interface for creating nodes, adding
typed operator edges, cloning graphs for non-committing intents, and exporting
snapshots if needed. It is intentionally minimal to allow later refactors of
the runtime to use this API instead of direct networkx access.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import networkx as nx


@dataclass
class NodeData:
    id: str
    kind: str
    acts: List[str]
    payload: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class EdgeData:
    operator: str
    runbook_id: str
    realizer_id: str
    diagnostics: Dict[str, Any]


class AOG:
    def __init__(self) -> None:
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self.operator_templates: List[Dict[str, Any]] = []

    def add_node(self, node: NodeData, status: str = "loaded") -> None:
        if node.id in self.graph.nodes:
            return
        self.graph.add_node(
            node.id,
            kind=node.kind,
            acts=node.acts,
            payload=node.payload,
            metadata=node.metadata,
            status=status,
        )

    def add_edge(self, source_id: str, target: NodeData, edge: EdgeData) -> None:
        self.add_node(target, status="live")
        self.graph.add_edge(
            source_id,
            target.id,
            operator=edge.operator,
            runbook_id=edge.runbook_id,
            realizer_id=edge.realizer_id,
            diagnostics=edge.diagnostics or {},
        )

    def record_operator_template(
        self,
        input_kind: str,
        output_kind: str,
        operator: str,
        runbook_id: str,
        realizer_id: str,
    ) -> None:
        self.operator_templates.append(
            {
                "input_kind": input_kind,
                "output_kind": output_kind,
                "operator": operator,
                "runbook_id": runbook_id,
                "realizer_id": realizer_id,
            }
        )

    def get_node(self, node_id: str) -> NodeData:
        data = self.graph.nodes[node_id]
        return NodeData(
            id=node_id,
            kind=data.get("kind"),
            acts=data.get("acts", []),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
        )

    def find_by_kind(self, kind: str) -> List[str]:
        return [node for node, data in self.graph.nodes(data=True) if data.get("kind") == kind]

    def clone(self) -> "AOG":
        clone = AOG()
        clone.graph = self.graph.copy()
        clone.operator_templates = list(self.operator_templates)
        return clone
