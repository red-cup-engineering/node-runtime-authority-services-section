"""
Aperiodic Operator Graph (AOG) core.

This module provides an in-memory graph with strict validation:
- Nodes are schema-validated carriers.
- Edges are typed operator instances linking existing nodes.
- IDs are canonical hashes; duplicates with conflicting payloads are rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, MutableMapping, Optional

from .canonical import assert_id_coherence
from .validation import validate_object
from .law_enforcement import enforce_node_laws


@dataclass(frozen=True)
class Edge:
    id: str
    operator: str
    src: str
    tgt: str
    runbook_id: str
    step_index: int
    evidence_ids: Optional[list[str]] = None

    @classmethod
    def from_payload(cls, payload: MutableMapping[str, object]) -> "Edge":
        assert_id_coherence(payload)
        return cls(
            id=str(payload["id"]),
            operator=str(payload["operator"]),
            src=str(payload["src"]),
            tgt=str(payload["tgt"]),
            runbook_id=str(payload["runbook_id"]),
            step_index=int(payload["step_index"]),
            evidence_ids=list(payload.get("evidence_ids", [])) if payload.get("evidence_ids") is not None else None,
        )


class RelationalGraph:
    """
    Minimal AOG representation with strict invariants.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, dict] = {}
        self.edges: Dict[str, Edge] = {}

    def add_node(self, payload: MutableMapping[str, object]) -> dict:
        """
        Insert a new node after validating schema and canonical ID.
        """
        assert_id_coherence(payload)
        validate_object(payload)
        # Enforce flow/nucleus/system laws at the graph boundary.
        enforce_node_laws(self, payload)
        node_id = payload["id"]
        existing = self.nodes.get(node_id)
        if existing is not None and existing != payload:
            raise ValueError(f"node {node_id} already exists with different payload")
        self.nodes[node_id] = dict(payload)
        return self.nodes[node_id]

    def update_node(self, payload: MutableMapping[str, object]) -> dict:
        """
        Update an existing node with a payload that has the same canonical ID.
        """
        assert_id_coherence(payload)
        node_id = payload["id"]
        if node_id not in self.nodes:
            raise KeyError(f"cannot update missing node {node_id}")
        validate_object(payload)
        if node_id != payload["id"]:
            raise ValueError("payload ID changed during validation")
        self.nodes[node_id] = dict(payload)
        return self.nodes[node_id]

    def add_edge(self, payload: MutableMapping[str, object]) -> Edge:
        """
        Insert an edge after ensuring endpoints exist and ID is canonical.
        """
        edge = Edge.from_payload(payload)
        if edge.src not in self.nodes or edge.tgt not in self.nodes:
            raise ValueError(f"edge endpoints must exist: {edge.src} -> {edge.tgt}")
        existing = self.edges.get(edge.id)
        if existing is not None and existing != edge:
            raise ValueError(f"edge {edge.id} already exists with different payload")
        self.edges[edge.id] = edge
        return edge
