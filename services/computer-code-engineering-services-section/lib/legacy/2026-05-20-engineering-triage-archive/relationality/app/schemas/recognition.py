"""TracePoint / recognition schema definitions.

In the runtime, what we historically called a "Recognition" is really a
*TracePoint*: a typed, triadic point in a trace/context, with attached
structure.  Each TracePoint must trace back to earned acts via the dependency
graph.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from app.util.deprecation import warn_legacy_feature


class TracePointRole(str, Enum):
    """Role of a TracePoint in the triad/context stack."""
    OBSERVATION = "observation"
    JUDGEMENT = "judgement"
    WITNESS = "witness"
    CONTEXT = "context"
    TRACE = "trace"


class TracePointStatus(str, Enum):
    """Lifecycle status of a TracePoint."""
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class TracePointBase(BaseModel):
    """Base fields shared by all TracePoint representations."""
    
    type: TracePointRole = Field(
        ...,
        description="The role of this TracePoint (observation, judgement, witness, context, trace)"
    )
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Human-readable title for the TracePoint"
    )
    
    content: dict[str, Any] = Field(
        default_factory=dict,
        description="The payload data for this TracePoint (structured terms, attributes, etc.)"
    )
    
    acts: list[str] = Field(
        default_factory=list,
        description="List of act slugs this TracePoint depends on (e.g., ['recognize-observation', 'seed-value'])"
    )
    
    parent_id: Optional[UUID] = Field(
        default=None,
        description="Parent TracePoint ID for hierarchical traces"
    )
    
    tags: list[str] = Field(
        default_factory=list,
        description="Classification tags for filtering and policy matching"
    )
    
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (schema version, source, etc.)"
    )
    
    @field_validator("acts")
    @classmethod
    def validate_acts_format(cls, v: list[str]) -> list[str]:
        """Ensure act slugs follow the expected format."""
        for act in v:
            if not act.replace("-", "").replace("_", "").isalnum():
                raise ValueError(f"Invalid act slug format: {act}")
        return v

    @model_validator(mode="after")
    def _warn_deprecated(cls, values: "TracePointBase"):  # type: ignore[override]
        """Emit a runtime warning whenever a TracePoint is instantiated.

        TracePoint-based carriers are being phased out in favour of
        RecognitionFiber-based representations; this makes their use
        visible whenever old code paths are exercised.
        """
        # Use a small helper so call sites stay consistent.
        warn_legacy_feature(
            "TracePoint",
            "Use RecognitionFiber-based carriers and the hypertensor sheaf instead.",
        )
        return values


class TracePointCreate(TracePointBase):
    """Schema for creating a new TracePoint."""
    
    policy_annotations: list[str] = Field(
        default_factory=list,
        description="Policy annotation IDs that authorize this TracePoint"
    )


class TracePointUpdate(BaseModel):
    """Schema for updating an existing TracePoint (partial update)."""
    
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    content: Optional[dict[str, Any]] = None
    acts: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    status: Optional[TracePointStatus] = None


class TracePointSchema(TracePointBase):
    """Full TracePoint schema including system-managed fields."""
    
    id: UUID = Field(default_factory=uuid4)
    
    status: TracePointStatus = Field(default=TracePointStatus.PENDING)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    snapshot_id: Optional[UUID] = Field(
        default=None,
        description="ID of the snapshot this TracePoint belongs to"
    )
    
    trace_id: Optional[UUID] = Field(
        default=None,
        description="Root trace ID for distributed tracing"
    )
    
    baseline_hash: Optional[str] = Field(
        default=None,
        description="Hash of the baseline state when this TracePoint was created"
    )
    
    class Config:
        from_attributes = True


def validate_tracepoint(data: dict[str, Any], known_acts: set[str]) -> tuple[bool, list[str]]:
    """Validate a TracePoint payload against the schema and known acts.
    
    Args:
        data: The TracePoint data to validate.
        known_acts: Set of known act slugs from the graph.
    
    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors: list[str] = []
    
    try:
        tracepoint = TracePointCreate.model_validate(data)
    except Exception as e:
        return False, [str(e)]
    
    unknown_acts = set(tracepoint.acts) - known_acts
    if unknown_acts:
        errors.append(f"Unknown acts referenced: {sorted(unknown_acts)}")
    
    if not tracepoint.acts:
        errors.append("TracePoint must reference at least one act")
    
    return len(errors) == 0, errors
