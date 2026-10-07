"""
Aperiodic Operator Graph (AOG) construction and manipulation.

Nodes correspond to recognition objects (acts → objects). Edges correspond to
typed operators (acts → operators) annotated with the realizer that enacted the
move. The AOG lives entirely in memory; persistent artifacts only seed the
initial skeleton.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import networkx as nx

from .models import RecognitionObject


class RelationalGraph:
    """Typed operator graph built from persistent artifacts."""

    def __init__(self) -> None:
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self.operator_templates: List[Dict[str, Any]] = []

    def add_object(self, obj: RecognitionObject, status: str = "loaded") -> None:
        if obj.id in self.graph.nodes:
            return
        self.graph.add_node(
            obj.id,
            kind=obj.kind,
            acts=obj.acts,
            payload=obj.payload,
            metadata=obj.metadata,
            status=status,
        )

    def record_operator_template(
        self,
        input_kind: str,
        output_kind: str,
        operator: str,
        runbook_id: str,
        realizer_id: str,
    ) -> None:
        """Keep a template of allowed typed edges derived from runbooks."""
        self.operator_templates.append(
            {
                "input_kind": input_kind,
                "output_kind": output_kind,
                "operator": operator,
                "runbook_id": runbook_id,
                "realizer_id": realizer_id,
            }
        )

    def clone(self) -> "RelationalGraph":
        """Create a shallow clone for intent modes that must not mutate the live AOG."""
        clone = RelationalGraph()
        clone.graph = self.graph.copy()
        clone.operator_templates = list(self.operator_templates)
        return clone

    def add_operator_edge(
        self,
        source_id: str,
        target: RecognitionObject,
        operator: str,
        runbook_id: str,
        realizer_id: str,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert a new node and connect it to the source via a typed edge."""
        self.add_object(target, status="live")
        self.graph.add_edge(
            source_id,
            target.id,
            operator=operator,
            runbook_id=runbook_id,
            realizer_id=realizer_id,
            diagnostics=diagnostics or {},
        )

    def get_node(self, node_id: str) -> RecognitionObject:
        data = self.graph.nodes[node_id]
        return RecognitionObject(
            id=node_id,
            kind=data["kind"],
            acts=data.get("acts", []),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
        )

    def find_by_kind(self, kind: str) -> List[str]:
        return [node for node, data in self.graph.nodes(data=True) if data.get("kind") == kind]
