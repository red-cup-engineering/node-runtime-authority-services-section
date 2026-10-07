"""Hypertensor-related schemas.

These datatypes implement the state representation from the
Quasicrystalline Hypertensor Simulation specification.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field

from app.schemas.tower import ProfileTower


class LatticeSite(BaseModel):
    """A single site in a lattice window."""

    index: Tuple[int, ...] = Field(
        ...,
        description="Lattice index in Z^d (as a tuple of ints)",
    )
    recognition_id: str = Field(
        ...,
        description="Stabilized recognition identifier at this site",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flow phase, nucleus flag, and other per-site metadata",
    )


class LatticeWindow(BaseModel):
    """Finite or symbolic lattice window for a hypertensor."""

    dimension: int = Field(..., description="Rank d of Z^d")
    sites: List[LatticeSite] = Field(
        default_factory=list,
        description="Materialized sites in the window",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Window-level metadata (e.g., substitution stage)",
    )


class PatternPatch(BaseModel):
    """A local patch pattern within the lattice."""

    relative_indices: List[Tuple[int, ...]] = Field(
        ...,
        description="Indices relative to a chosen origin inside the patch",
    )
    recognition_ids: List[str] = Field(
        ...,
        description="Recognitions at each relative index",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Auxiliary info (e.g., flow phase, nucleus flags)",
    )


class PatternCatalogueEntry(BaseModel):
    """Canonical representation of a patch and its statistics."""

    id: str = Field(..., description="Canonical patch identifier")
    patch: PatternPatch
    frequency: float = Field(
        ...,
        description="Estimated relative frequency of this patch",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostics about aperiodicity, density, discreteness",
    )


class SheafSection(BaseModel):
    """A finite section of the quasicrystalline hypertensor sheaf.

    This combines a lattice window with one or more profile towers attached to
    fibres within that window.  It is a concrete carrier for small pieces of
    the relational hypertensor sheaf S.
    """

    window: LatticeWindow = Field(
        ...,
        description="Finite lattice window over which this section is defined",
    )
    towers: List[ProfileTower] = Field(
        default_factory=list,
        description="Profile towers attached to fibres in this window",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Section-level metadata (e.g., chart identifiers, domain tags)",
    )
