"""Tower-related schemas.

These datatypes implement the state representations from the tower and
modality specifications: profile towers, nested/composite towers, and
modality towers over predicates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ProfileLevel(BaseModel):
    """One level in a profile tower."""

    level: int = Field(..., description="Height index within the tower")
    profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="Profile data at this level (domain-specific)",
    )
    witnesses: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recognitions witnessing this level (e.g., acts)",
    )


class ProfileTower(BaseModel):
    """Profile tower as described in the tower interaction machinery."""

    id: str = Field(..., description="Tower identifier")
    fiber_id: Optional[str] = Field(
        default=None,
        description="Identifier of the trace/context fibre this tower is attached to",
    )
    base_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="Base profile at level 0",
    )
    height: int = Field(..., description="Number of levels in the tower")
    levels: List[ProfileLevel] = Field(
        default_factory=list,
        description="Levels in the tower",
    )
    built_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when this tower was constructed (if known)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional tower metadata (domain-specific)",
    )


class NestedProfileTower(BaseModel):
    """Nested profile tower: a tower nested within another."""

    id: str = Field(..., description="Nested tower identifier")
    outer_tower_id: str = Field(..., description="Identifier of outer tower")
    inner_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="Inner profile that is nested",
    )
    nesting_level: int = Field(
        ...,
        description="Level at which nesting occurs",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompositeProfileTower(BaseModel):
    """Composite profile tower built from component towers."""

    id: str = Field(..., description="Composite tower identifier")
    component_tower_ids: List[str] = Field(
        default_factory=list,
        description="IDs of component towers",
    )
    composition_type: Literal["sequential", "parallel"] = Field(
        "sequential",
        description="How component towers are composed",
    )
    component_count: int = Field(..., description="Number of component towers")
    metadata: Dict[str, Any] = Field(default_factory=dict)
