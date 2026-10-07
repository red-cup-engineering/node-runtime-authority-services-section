"""Topology integration schemas.

These datatypes implement the state representation from the topology
integration specification: strata/tower catalog, sheaf fibers, and
constraint sets.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class StratumEntry(BaseModel):
    """Entry in the strata/tower catalog for a module."""

    module_id: str = Field(..., description="Identifier of the module")
    tower_level: int = Field(..., description="Profile tower level for module")
    coverage: Dict[str, Any] = Field(
        default_factory=dict,
        description="Coverage data for this stratum (e.g., sites/cells)",
    )
    witnesses: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flow/nucleus witnesses for this stratum",
    )


class SheafFiber(BaseModel):
    """Sheaf fiber / glued section entry."""

    object_id: str = Field(..., description="Base object identifier")
    cover_id: str = Field(..., description="Cover identifier")
    section_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Glued section data for this cover",
    )


class Constraint(BaseModel):
    """Single constraint in the topology integration output."""

    kind: Literal["ordering", "placement", "locality"] = Field(
        ...,
        description="Constraint kind: execution order, placement, or locality",
    )
    subject: str = Field(..., description="Primary module or dataset id")
    target: str = Field(..., description="Secondary module/dataset/id")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Constraint details (e.g., before/after, region)",
    )


class ConstraintBundle(BaseModel):
    """Bundle of constraints for schedulers/resource managers."""

    constraints: List[Constraint] = Field(
        default_factory=list,
        description="List of constraints",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Bundle-level metadata (e.g., derived_at, trace_id)",
    )

