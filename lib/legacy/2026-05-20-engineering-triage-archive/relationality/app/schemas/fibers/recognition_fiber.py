from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.schemas.fibers.act_tree_node import ActTreeNode


class RecognitionRole(str):
    """Role of a recognition fibre in the triad/context stack."""

    OBSERVATION = "observation"
    JUDGEMENT = "judgement"
    WITNESS = "witness"
    CONTEXT = "context"
    TRACE = "trace"


class RecognitionFiber(BaseModel):
    """Single fibre of recognition in the hypertensor sheaf.

    This is the math-native carrier that replaces ad-hoc dict payloads
    for recognition-like structures.
    """

    id: UUID = Field(default_factory=uuid4, description="Stable fibre identifier")

    role: str = Field(
        ...,
        description=(
            "Role of this fibre (observation, judgement, witness, context, trace)"
        ),
    )

    acts: List[str] = Field(
        default_factory=list,
        description="Earned act slugs for this fibre",
    )

    tree: List[ActTreeNode] = Field(
        default_factory=list,
        description="Derivation tree for the main act of this fibre",
    )

    payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Typed payload carried by this fibre (model-dumped)",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation time of this fibre",
    )
