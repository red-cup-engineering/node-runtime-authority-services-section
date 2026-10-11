"""Traceability graph schemas.

These datatypes implement the state representation from the
Traceability Graph Simulation specification: node catalog, edges,
and policy ledger entries.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TraceNode(BaseModel):
    """A node in the traceability graph (act/theorem/spec/arch/etc.)."""

    id: str = Field(..., description="Stable node identifier")
    path: Optional[str] = Field(
        default=None,
        description="Source path (for doc-backed nodes)",
    )
    node_type: Literal["act", "theorem", "specification", "architecture", "idea"] = (
        Field(..., description="Kind of node in the trace graph")
    )
    frontmatter: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parsed metadata/frontmatter",
    )
    policy_tags: List[str] = Field(
        default_factory=list,
        description="Policy-related tags/disciplines attached to this node",
    )


class TraceEdge(BaseModel):
    """Directed labelled edge in the traceability graph."""

    src_id: str = Field(..., description="Source node id")
    dst_id: str = Field(..., description="Destination node id")
    edge_type: Literal["depends_on", "operation", "top", "bottom"] = Field(
        "depends_on",
        description="Justification label for the edge",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional edge metadata (e.g., act relation)",
    )


class PolicyLedgerEntry(BaseModel):
    """Entry in the traceability policy ledger."""

    node_id: str = Field(..., description="Node affected by this entry")
    approved_by: str = Field(..., description="Approver identifier")
    approved_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of approval",
    )
    disciplines: List[str] = Field(
        default_factory=list,
        description="Policy disciplines implicated",
    )
    justification: Optional[str] = Field(
        default=None,
        description="Free-text justification for this change",
    )

