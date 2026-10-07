from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ActTreeNode(BaseModel):
    """Single node in an act derivation tree.

    Each node names an act (by slug) and may have zero or more child nodes.
    This lets higher-level acts inspect the concrete derivation footprint,
    not just a flat list of act labels.
    """

    act: str = Field(..., description="Act slug for this node")
    children: List["ActTreeNode"] = Field(
        default_factory=list,
        description="Child nodes in the derivation tree",
    )


ActTreeNode.model_rebuild()

