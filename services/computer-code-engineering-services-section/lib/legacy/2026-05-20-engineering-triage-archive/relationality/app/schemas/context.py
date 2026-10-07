"""Context and parametric runtime schemas.

These datatypes implement the state representations from the parametric
semantics and parametric runtime specifications: base contexts, fibres,
and parametric contexts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Context(BaseModel):
    """Base runtime context (tenant/environment/domain/profile)."""

    id: str = Field(..., description="Context identifier")
    tenant: Optional[str] = Field(
        default=None,
        description="Tenant or user id owning this context",
    )
    domain: Optional[str] = Field(
        default=None,
        description="Domain slice (e.g., physics, finance)",
    )
    profile_id: Optional[str] = Field(
        default=None,
        description="Profile/tower id for this context",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context metadata",
    )


class ContextFiber(BaseModel):
    """Fibre over a base context in the indexed category."""

    id: str = Field(..., description="Fibre identifier")
    context_id: str = Field(..., description="Base context id")
    bindings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Term/judgement bindings in this fibre",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Fibre-specific metadata (effects, coeffects, etc.)",
    )


class ParametricContext(BaseModel):
    """Parametric context with fibre indexing."""

    base: Context
    fibre: ContextFiber
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parametric indices (e.g., environment, modality indices)",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this parametric context was built",
    )

